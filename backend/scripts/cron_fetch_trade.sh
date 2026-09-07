#!/bin/bash
set -euo pipefail
cd /home/ubuntu/sales-analysis
for name in WANGDIAN_SID WANGDIAN_APPKEY WANGDIAN_APPSECRET; do
  value=$(sed -n "s/^${name}=//p" .env | tail -n 1)
  if [ -z "$value" ]; then
    echo "Missing $name in .env" >&2
    exit 1
  fi
  printf -v "$name" '%s' "$value"
  export "$name"
done
YESTERDAY=$(date -d 'yesterday' +%Y-%m-%d)
REFUND_START=$(date -d 'yesterday -30 days' +%Y-%m-%d)
.venv/bin/python3 scripts/fetch_trade_daily.py --start $YESTERDAY --end $YESTERDAY --shop 慕咖 >> /tmp/cron_trade.log 2>&1
sleep 60
.venv/bin/python3 scripts/fetch_trade_daily.py --start $YESTERDAY --end $YESTERDAY --shop 巴恩 >> /tmp/cron_trade.log 2>&1
sleep 60
.venv/bin/python3 scripts/fetch_trade_daily.py --start $YESTERDAY --end $YESTERDAY --shop 稻壳 >> /tmp/cron_trade.log 2>&1
sleep 60
# 退款单：拉最近30天（覆盖待处理状态流转，按refund_no去重取最新）
.venv/bin/python3 scripts/fetch_refund_daily.py --start $REFUND_START --end $YESTERDAY >> /tmp/cron_trade.log 2>&1
