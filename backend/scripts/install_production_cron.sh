#!/bin/bash
set -euo pipefail

APP_DIR=/home/ubuntu/sales-analysis
CRON_TMP=$(mktemp)
trap 'rm -f "$CRON_TMP"' EXIT

crontab -l 2>/dev/null \
  | grep -v '/api/v1/inventory/sync-from-wangdian' \
  | grep -v '/scripts/cron_sync_inventory.sh' \
  | grep -v '/scripts/cron_fetch_trade.sh' \
  | grep -v '/scripts/cron_fetch_today.sh' > "$CRON_TMP" || true

cat >> "$CRON_TMP" <<'EOF'
0 1 * * * /home/ubuntu/sales-analysis/scripts/cron_sync_inventory.sh
30 1 * * * /home/ubuntu/sales-analysis/scripts/cron_fetch_trade.sh
10 8-23 * * * /home/ubuntu/sales-analysis/scripts/cron_fetch_today.sh
EOF

crontab "$CRON_TMP"
chmod 750 \
  "$APP_DIR/scripts/cron_sync_inventory.sh" \
  "$APP_DIR/scripts/cron_fetch_trade.sh" \
  "$APP_DIR/scripts/cron_fetch_today.sh"

echo "Production cron jobs installed."
