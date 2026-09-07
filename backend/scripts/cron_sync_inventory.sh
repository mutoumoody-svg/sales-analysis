#!/bin/bash
set -euo pipefail

APP_DIR=/home/ubuntu/sales-analysis
LOG=/tmp/wangdian_sync.log

set -a
source "$APP_DIR/.env"
set +a

if [ -z "${ADMIN_API_KEY:-}" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ADMIN_API_KEY is missing" > "$LOG"
  exit 1
fi

/usr/bin/curl --fail --silent --show-error \
  -X POST \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  http://127.0.0.1:8000/api/v1/inventory/sync-from-wangdian > "$LOG" 2>&1
