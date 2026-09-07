#!/bin/bash
set -euo pipefail
# 日内刷新：抓取当天出库明细 + 三品牌订单 + 当天退款，每次运行覆盖更新当天文件
# 用途：让实时销售页/店铺日报当天数据准实时可见（延迟约1小时）
cd /home/ubuntu/sales-analysis
TODAY=$(date +%Y-%m-%d)
LOG=/tmp/cron_fetch_today.log
echo "[$(date "+%Y-%m-%d %H:%M:%S")] === 日内刷新 $TODAY ===" >> "$LOG"

# 1. 当天出库明细（实时销售页数据源，end_time自动截断到now-3min）
cd /opt/kucun/scripts
python3 fetch_wdt_daily_outbound.py --date "$TODAY" >> "$LOG" 2>&1

# 2. 三品牌当天订单
cd /home/ubuntu/sales-analysis
.venv/bin/python3 scripts/fetch_trade_daily.py --start "$TODAY" --end "$TODAY" --shop 慕咖 >> "$LOG" 2>&1
sleep 60
.venv/bin/python3 scripts/fetch_trade_daily.py --start "$TODAY" --end "$TODAY" --shop 巴恩 >> "$LOG" 2>&1
sleep 60
.venv/bin/python3 scripts/fetch_trade_daily.py --start "$TODAY" --end "$TODAY" --shop 稻壳 >> "$LOG" 2>&1
sleep 60

# 3. 当天退款单（文件按日去重取最新fetched_at，不会重复计数）
.venv/bin/python3 scripts/fetch_refund_daily.py --start "$TODAY" --end "$TODAY" >> "$LOG" 2>&1
echo "[$(date "+%Y-%m-%d %H:%M:%S")] === 完成 ===" >> "$LOG"
