#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-$ROOT_DIR/build/public-release}"

mkdir -p "$(dirname "$TARGET_DIR")"
TARGET_DIR="$(cd "$(dirname "$TARGET_DIR")" && pwd)/$(basename "$TARGET_DIR")"

if [[ "$TARGET_DIR" == "$ROOT_DIR" ]]; then
  echo "Refusing to stage public release into the repository root" >&2
  exit 1
fi

rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

rsync -a \
  --exclude ".git/" \
  --exclude ".vscode/" \
  --exclude ".venv/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude ".DS_Store" \
  --exclude ".public-release*" \
  --exclude "build/" \
  --exclude "certs/" \
  --exclude ".env.local" \
  --exclude "feedback.jsonl" \
  --exclude "nohup.out" \
  --exclude "uvicorn.log" \
  "$ROOT_DIR/" "$TARGET_DIR/"

paths_to_remove=(
  "corpora"
  "corpora copy"
  "eternal_patrol.jsonl"
  "lost_submarines-3.sql"
  "docs/ProjectCosts.md"
  "docs/ProjectCostsApprovalMemo.md"
  "docs/todo.md"
  "AI_CONTEXT.md"
  "add_faqs.py"
  "add_faqs2.py"
  "add_faqs3.py"
  "add_faqs4.py"
  "add_faqs5.py"
  "add_faqs6.py"
  "add_faqs7.py"
  "add_faqs8.py"
  "add_faqs9.py"
  "add_faqs10.py"
  "debug_batch5.py"
  "debug_fails.py"
  "fix_batch5.py"
  "fix_batch6.py"
  "fix_batch6b.py"
  "fix_batch7.py"
  "fix_corpus_pam112.py"
  "fix_regressions.py"
  "fix_titles2.py"
  "score_debug.py"
  "spot_check.py"
  "spot_check2.py"
  "test_batch4.py"
  "test_batch5.py"
  "test_batch5_eval.py"
  "test_batch6.py"
  "test_batch6_eval.py"
  "test_batch7.py"
  "test_batch7_eval.py"
  "test_batch8.py"
  "test_batch8_eval.py"
  "test_batch9.py"
  "test_batch9_eval.py"
  "test_batch10.py"
  "test_batch10_eval.py"
  "test_batch11.py"
  "test_batch11_eval.py"
  "test_batch12.py"
  "test_batch12_eval.py"
)

for path in "${paths_to_remove[@]}"; do
  rm -rf "$TARGET_DIR/$path"
done

cat <<EOF
Staged public-release tree at:
  $TARGET_DIR

Known private content removed from the staged tree:
  - corpora/
  - corpora copy/
  - eternal_patrol.jsonl
  - lost_submarines-3.sql
  - docs/ProjectCosts.md
  - docs/ProjectCostsApprovalMemo.md
  - docs/todo.md
  - AI_CONTEXT.md
  - internal FAQ migration, debug, and batch evaluation scripts

Manual review still required before publishing:
  - web/videos/
  - web/images/
  - any remaining one-off maintenance scripts not needed by outside contributors
EOF