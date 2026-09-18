#!/usr/bin/env bash
# upload_videos_r2.sh — sync web/videos/*.mp4 to a Cloudflare R2 bucket.
#
# Setup (one-time):
#   1. Create an R2 bucket in the Cloudflare dashboard.
#   2. Enable public access (R2 → bucket → Settings → Public Access)
#      OR attach a custom domain (recommended for caching).
#   3. Create an R2 API token (R2 → Manage R2 API Tokens → Object Read & Write).
#   4. Copy .env.example values into .env.local:
#        R2_ACCOUNT_ID=...
#        R2_ACCESS_KEY_ID=...
#        R2_SECRET_ACCESS_KEY=...
#        R2_BUCKET=pampanito-videos
#   5. Install AWS CLI: brew install awscli
#
# Usage: ./scripts/upload_videos_r2.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env.local ]; then
  set -a; source .env.local; set +a
fi

: "${R2_ACCOUNT_ID:?set R2_ACCOUNT_ID in .env.local}"
: "${R2_ACCESS_KEY_ID:?set R2_ACCESS_KEY_ID in .env.local}"
: "${R2_SECRET_ACCESS_KEY:?set R2_SECRET_ACCESS_KEY in .env.local}"
: "${R2_BUCKET:?set R2_BUCKET in .env.local}"

ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
aws s3 sync web/videos/ "s3://${R2_BUCKET}/" \
  --endpoint-url "$ENDPOINT" \
  --exclude "*" \
  --include "*.mp4" \
  --content-type "video/mp4" \
  --cache-control "public, max-age=31536000, immutable"

echo
echo "Uploaded. Set window.PAMPANITO_VIDEO_BASE in web/video-config.js to your"
echo "bucket's public URL (e.g. https://pub-<hash>.r2.dev or your custom domain)."
