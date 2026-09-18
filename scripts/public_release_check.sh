#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-$ROOT_DIR/build/public-release}"
PORT="${PUBLIC_RELEASE_CHECK_PORT:-8011}"
PYTHON_BIN="${PYTHON_BIN:-}"
TMP_DIR="$(mktemp -d)"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

bash "$ROOT_DIR/scripts/public_release_stage.sh" "$TARGET_DIR" >/dev/null

TARGET_DIR="$(cd "$(dirname "$TARGET_DIR")" && pwd)/$(basename "$TARGET_DIR")"
LOG_FILE="$TMP_DIR/public-release-check.log"
HEALTH_FILE="$TMP_DIR/public-release-health.json"
ADMIN_HEADERS="$TMP_DIR/public-release-admin.headers"
FEEDBACK_HEADERS="$TMP_DIR/public-release-feedback.headers"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
    wait "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

cd "$TARGET_DIR"
"$PYTHON_BIN" -m uvicorn api.main:app --host 127.0.0.1 --port "$PORT" >"$LOG_FILE" 2>&1 &
SERVER_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/health" -o "$HEALTH_FILE"; then
    break
  fi
  sleep 1
done

if [[ ! -s "$HEALTH_FILE" ]]; then
  echo "Public release check failed: server did not become ready" >&2
  cat "$LOG_FILE" >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY' "$HEALTH_FILE" "$PORT"
import json
import sys
import urllib.request

health_path = sys.argv[1]
port = sys.argv[2]

with open(health_path, "r", encoding="utf-8") as handle:
    health = json.load(handle)

assert health["status"] == "ok", health
assert health["sample_content_mode"] is True, health
assert health["auto_sample_fallback"] is True, health
assert health["faq_chunks"] >= 1, health
assert health["tour_chunks"] >= 1, health
assert health["corpora_dir"].endswith("sample_data/corpora"), health

def fetch(url: str):
    with urllib.request.urlopen(url) as response:
        return json.load(response)

faqs = fetch(f"http://127.0.0.1:{port}/api/faqs")
incidents = fetch(f"http://127.0.0.1:{port}/api/incidents")
eternal_patrol = fetch(f"http://127.0.0.1:{port}/api/eternal-patrol")

assert isinstance(faqs, list) and faqs, faqs
assert isinstance(incidents, dict) and incidents.get("incidents"), incidents
assert isinstance(eternal_patrol, list) and eternal_patrol, eternal_patrol
PY

admin_status="$(curl -sS -D "$ADMIN_HEADERS" -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/admin/faqs")"
if [[ "$admin_status" != "503" ]]; then
  echo "Expected /admin/faqs to return 503 without admin credentials, got $admin_status" >&2
  cat "$LOG_FILE" >&2
  exit 1
fi

if ! grep -qi '^www-authenticate: Basic realm="SubmarineDocent Admin"' "$ADMIN_HEADERS"; then
  echo "Missing admin auth challenge header on /admin/faqs" >&2
  cat "$ADMIN_HEADERS" >&2
  exit 1
fi

feedback_status="$(curl -sS -D "$FEEDBACK_HEADERS" -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/feedback/list")"
if [[ "$feedback_status" != "503" ]]; then
  echo "Expected /feedback/list to return 503 without admin credentials, got $feedback_status" >&2
  cat "$LOG_FILE" >&2
  exit 1
fi

if ! grep -qi '^www-authenticate: Basic realm="SubmarineDocent Admin"' "$FEEDBACK_HEADERS"; then
  echo "Missing admin auth challenge header on /feedback/list" >&2
  cat "$FEEDBACK_HEADERS" >&2
  exit 1
fi

echo "Public release check passed for $TARGET_DIR"