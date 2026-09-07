#!/bin/bash
set -euo pipefail

APP_DIR=/home/ubuntu/sales-analysis
LOG=/tmp/wangdian_sync.log

ADMIN_KEY=$(sed -n 's/^ADMIN_API_KEY=//p' "$APP_DIR/.env" | tail -n 1)
if [ -z "$ADMIN_KEY" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ADMIN_API_KEY is missing" > "$LOG"
  exit 1
fi

/usr/bin/curl --fail --silent --show-error \
  -X POST \
  -H "X-Admin-Key: $ADMIN_KEY" \
  http://127.0.0.1:8000/api/v1/inventory/sync-from-wangdian > "$LOG" 2>&1
