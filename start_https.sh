#!/usr/bin/env bash
# start_https.sh — start combined API + static file server over HTTPS
# Usage: ./start_https.sh

set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-.venv/bin/python3}"
LOCAL_HTTPS_HOST="${LOCAL_HTTPS_HOST:-localhost}"
LOCAL_HTTPS_PORT="${LOCAL_HTTPS_PORT:-8443}"
LOCAL_STATIC_PORT="${LOCAL_STATIC_PORT:-8444}"
SSL_KEYFILE="${SSL_KEYFILE:-certs/key.pem}"
SSL_CERTFILE="${SSL_CERTFILE:-certs/cert.pem}"

detect_lan_ip() {
  local ip
  for iface in en0 en1; do
    ip=$(ipconfig getifaddr "$iface" 2>/dev/null || true)
    if [ -n "$ip" ]; then
      echo "$ip"
      return 0
    fi
  done
  return 1
}

# Load secrets from .env.local (never committed to git)
if [ -f .env.local ]; then
  # shellcheck disable=SC1091
  set -a && source .env.local && set +a
fi

# Fallback: set these here only for local dev if .env.local is absent
# export GROQ_API_KEY=""     # get a free key at console.groq.com
# export SMTP_USER=""
# export SMTP_PASS=""

# Kill anything already on the HTTPS port
lsof -ti:"$LOCAL_HTTPS_PORT" | xargs kill -9 2>/dev/null || true
# Also kill old separate static server if running
lsof -ti:"$LOCAL_STATIC_PORT" | xargs kill -9 2>/dev/null || true

echo "======================================================"
echo " submarinedocent.org — local HTTPS server"
echo "======================================================"
echo ""
echo " Open in a browser:"
echo ""
echo "   https://${LOCAL_HTTPS_HOST}:${LOCAL_HTTPS_PORT}/"
if [ "$LOCAL_HTTPS_HOST" = "localhost" ] || [ "$LOCAL_HTTPS_HOST" = "127.0.0.1" ]; then
  LAN_IP="$(detect_lan_ip || true)"
  if [ -n "$LAN_IP" ]; then
    echo ""
    echo "   If you are using another device (phone/tablet), use your Mac's LAN IP instead:"
    echo "   https://${LAN_IP}:${LOCAL_HTTPS_PORT}/"
  fi
fi
echo ""
echo " API base URL (in Settings on the page):"
echo "   https://${LOCAL_HTTPS_HOST}:${LOCAL_HTTPS_PORT}"
echo ""
echo " Press Ctrl-C to stop."
echo "======================================================"
echo ""

$PYTHON -m uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "$LOCAL_HTTPS_PORT" \
  --ssl-keyfile "$SSL_KEYFILE" \
  --ssl-certfile "$SSL_CERTFILE" \
  --log-level warning