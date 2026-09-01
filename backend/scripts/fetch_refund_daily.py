#!/usr/bin/env python3
"""旺店通退款单抓取脚本 - 店铺日报退款数据源.

用法:
    python3 fetch_refund_daily.py --start 2026-08-01 --end 2026-08-23
    cron 每天拉取最近 30 天（覆盖待处理状态流转，按 refund_no 去重保留最新）

说明:
    - 使用 refund_query.php 按 modified 时间分段拉取（15天窗口）
    - 按 refund_no 去重，保留最新 modified 的记录（状态会流转）
    - 退款金额口径: status in (0,5) 且 actual_refund_amount > 0
      0=待处理(小红书等平台已退款、等收货确认), 5=已完成
      排除 1=待财审, 3=已取消, 4=已驳回
    - 归属日期按 refund_time（退款发生时间）
    - 输出: /opt/sales-analysis/output/refund_daily/{start}_{end}_refund.json
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services.wangdian_client import WangdianClient

# 从环境变量读凭证（不要在代码里硬编码，公开仓库会泄露）
SID = os.environ.get("WANGDIAN_SID", "")
APPKEY = os.environ.get("WANGDIAN_APPKEY", "")
APPSECRET = os.environ.get("WANGDIAN_APPSECRET", "")

OUTPUT_DIR = Path("/opt/sales-analysis/output/refund_daily")

EXCLUDED_SHOPS = ("天猫", "拼多多", "快团团")
# 计入退款金额的状态: 0=待处理(平台已退款) 5=已完成
COUNTED_STATUS = {"0", "5"}
# 待审状态（单独统计，不计入退款金额）
PENDING_STATUS = {"1", "2"}


def _request_page(client, start, end, page, retries=3):
    """带重试的单页请求（应对503限流）."""
    for i in range(retries):
        try:
            return client._request("/refund_query.php", {
                "start_time": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
                "page_size": "100",
                "page_no": str(page),
            })
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  请求失败({e})，{15 * (i + 1)}秒后重试...", flush=True)
            time.sleep(15 * (i + 1))


def fetch_refunds(client, start, end):
    """按15天窗口拉取 [start, end) 的退款单，按 refund_no 去重."""
    refunds = {}
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=15), end)
        page = 0
        while True:
            data = _request_page(client, cur, nxt, page)
            lst = data.get("refunds", [])
            for r in lst:
                shop = r.get("shop_name", "") or ""
                if any(k in shop for k in EXCLUDED_SHOPS):
                    continue
                no = str(r.get("refund_no") or r.get("refund_id") or "")
                if not no:
                    continue
                existing = refunds.get(no)
                if existing is None or str(r.get("modified", "")) > str(existing.get("modified", "")):
                    refunds[no] = r
            if not lst or len(lst) < 100:
                break
            page += 1
            time.sleep(0.5)
        print(f"  窗口 {cur:%m-%d}~{nxt:%m-%d} 完成，累计 {len(refunds)} 条", flush=True)
        cur = nxt
        time.sleep(1)
    return refunds


def summarize(refunds, date_start=None, date_end=None):
    """按日+店铺聚合退款."""
    daily = defaultdict(lambda: {"refund_count": 0, "refund_amount": 0.0,
                                 "pending_count": 0, "pending_amount": 0.0,
                                 "shops": defaultdict(lambda: {"count": 0, "amount": 0.0})})
    excluded = 0

    for r in refunds.values():
        # 归属日期: refund_time 优先，无则用 created
        rt = str(r.get("refund_time") or "")
        date = rt[:10] if rt >= "2000-01-01" else str(r.get("created") or "")[:10]
        if not date or date < "2000-01-01":
            excluded += 1
            continue
        if date_start and date < date_start:
            excluded += 1
            continue
        if date_end and date > date_end:
            excluded += 1
            continue

        shop = r.get("shop_name", "") or ""
        status = str(r.get("status"))
        amt = float(r.get("actual_refund_amount") or 0)

        d = daily[date]
        if status in COUNTED_STATUS and amt > 0:
            d["refund_count"] += 1
            d["refund_amount"] += amt
            d["shops"][shop]["count"] += 1
            d["shops"][shop]["amount"] += amt
        elif status in PENDING_STATUS:
            d["pending_count"] += 1
            d["pending_amount"] += amt

    out = {}
    for date, d in sorted(daily.items()):
        out[date] = {
            "refund_count": d["refund_count"],
            "refund_amount": round(d["refund_amount"], 2),
            "pending_count": d["pending_count"],
            "pending_amount": round(d["pending_amount"], 2),
            "shops": {s: {"count": v["count"], "amount": round(v["amount"], 2)}
                      for s, v in sorted(d["shops"].items(), key=lambda x: -x[1]["amount"])},
        }
    return out, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD（含当天）")
    args = ap.parse_args()

    # modified 拉取窗口：end 后加1天（覆盖当天结束前的修改）；end_time 不能晚于当前时间-2分钟
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d") + timedelta(days=1)
    now = datetime.now() - timedelta(minutes=3)
    if end > now:
        end = now
    if start >= end:
        print("起始时间晚于当前时间，无可拉取数据")
        return

    client = WangdianClient(sid=SID, appkey=APPKEY, appsecret=APPSECRET)
    print(f"拉取 {args.start} ~ {args.end} 退款单（按modified）", flush=True)

    refunds = fetch_refunds(client, start, end)
    print(f"共拉到 {len(refunds)} 条去重退款单", flush=True)
    if not refunds:
        return

    daily, excluded = summarize(refunds, args.start, args.end)
    print(f"{excluded} 条归属日期不在范围内，已排除", flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{args.start}_{args.end}_refund.json"
    result = {
        "fetched_at": datetime.now().isoformat(),
        "range": {"start": args.start, "end": args.end},
        "total_refunds": len(refunds),
        "daily": daily,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"已保存: {out_file}", flush=True)

    print("\n=== 每日退款汇总 ===")
    print(f"{'日期':<12}{'退款单':>6}{'退款金额':>12}{'待审单':>6}{'待审金额':>10}")
    total_amt = 0.0
    for date, d in daily.items():
        total_amt += d["refund_amount"]
        print(f"{date:<12}{d['refund_count']:>6}{d['refund_amount']:>12,.0f}"
              f"{d['pending_count']:>6}{d['pending_amount']:>10,.0f}")
    print(f"合计退款: ¥{total_amt:,.2f}")


if __name__ == "__main__":
    main()
