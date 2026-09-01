#!/bin/bash
cd /home/ubuntu/sales-analysis
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
