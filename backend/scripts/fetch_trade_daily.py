#!/usr/bin/env python3
"""旺店通订单抓取脚本 - 每日店铺日报数据源.

用法:
    python3 fetch_trade_daily.py --start 2026-08-01 --end 2026-08-22 --shop 慕咖
    python3 fetch_trade_daily.py --start 2026-08-22 --end 2026-08-22  # 昨天，不过滤店铺

说明:
    - 使用 trade_query.php 按 modified 时间 60 分钟窗口分段拉取
    - 淘系/拼多多订单旺店通API本身不返回，无需额外过滤
    - 按 trade_no 去重（订单多次修改会在多个 modified 窗口出现）
    - 输出: /opt/sales-analysis/output/trade_daily/{start}_{end}_{tag}.json
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

OUTPUT_DIR = Path("/opt/sales-analysis/output/trade_daily")

# 订单状态映射（旺店通 trade_status）
TRADE_STATUS = {
    1: "待审核", 2: "待财审", 3: "待推送", 4: "已推送",
    5: "部分发货", 6: "已发货", 7: "已完成", 8: "已取消", 9: "已暂停",
}
# 退款状态
REFUND_STATUS = {0: "无退款", 1: "部分退款", 2: "全部退款"}


def fetch_range(client, start, end, shop_filter=None):
    """按60分钟窗口拉取 [start, end) 的订单，按 trade_no 去重."""
    orders = {}
    cur = start
    windows = 0

    def _request_with_retry(params, retries=3):
        """带重试的单页请求（应对503限流）."""
        for i in range(retries):
            try:
                return client._request("/trade_query.php", params)
            except Exception as e:
                if i == retries - 1:
                    raise
                print(f"  请求失败({e})，{15 * (i + 1)}秒后重试...", flush=True)
                time.sleep(15 * (i + 1))

    while cur < end:
        nxt = min(cur + timedelta(minutes=60), end)
        page = 0
        while True:
            data = _request_with_retry({
                "start_time": cur.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": nxt.strftime("%Y-%m-%d %H:%M:%S"),
                "page_size": "100",
                "page_no": str(page),
            })
            trades = data.get("trades", [])
            for t in trades:
                shop = t.get("shop_name", "")
                if shop_filter and shop_filter not in shop:
                    continue
                # 排除淘系/拼多多店铺档案（虽然API本身不返回其订单，保险起见）
                if any(k in shop for k in ("天猫", "拼多多", "快团团")):
                    continue
                tn = t.get("trade_no", "")
                if not tn:
                    continue
                # 同一订单可能多次拉到（modified更新），保留最新的
                existing = orders.get(tn)
                new_time = t.get("modified", "")
                if existing is None or str(new_time) > str(existing.get("modified", "")):
                    orders[tn] = t
            if not trades or len(trades) < 100:
                break
            page += 1
        windows += 1
        if windows % 24 == 0:
            print(f"  进度: {cur.strftime('%m-%d %H:%M')} 已拉 {len(orders)} 单", flush=True)
        cur = nxt
    return orders


def summarize(orders, date_start=None, date_end=None):
    """按日+店铺 / SKU 聚合. 只保留归属日期在 [date_start, date_end] 内的订单（按付款时间）."""
    daily = defaultdict(lambda: {"order_count": 0, "paid": 0.0, "refund_full": 0,
                                  "refund_part": 0, "shops": defaultdict(lambda: {"count": 0, "paid": 0.0})})
    skus = defaultdict(lambda: {"name": "", "qty": 0, "amount": 0.0, "orders": 0})
    sku_daily = defaultdict(lambda: defaultdict(lambda: {"qty": 0, "amount": 0.0}))
    excluded = 0

    for t in orders.values():
        pay_time = t.get("pay_time", "") or t.get("trade_time", "")
        date = str(pay_time)[:10]
        if not date or date < "2000-01-01":
            excluded += 1  # 无有效时间的单（未付款等）
            continue
        if date_start and date < date_start:
            excluded += 1
            continue
        if date_end and date > date_end:
            excluded += 1
            continue
        shop = t.get("shop_name", "")
        paid = float(t.get("paid", 0) or 0)
        rs = t.get("refund_status", 0)

        d = daily[date]
        d["order_count"] += 1
        d["paid"] += paid
        if rs == 2:
            d["refund_full"] += 1
        elif rs == 1:
            d["refund_part"] += 1
        d["shops"][shop]["count"] += 1
        d["shops"][shop]["paid"] += paid

        # 明细
        for ol in (t.get("goods_list") or []):
            sku = str(ol.get("spec_no", "") or ol.get("goods_no", ""))
            if not sku:
                continue
            qty = float(ol.get("num", 0) or 0)
            amt = float(ol.get("paid", 0) or 0)
            skus[sku]["name"] = ol.get("goods_name", "")
            skus[sku]["qty"] += qty
            skus[sku]["amount"] += amt
            skus[sku]["orders"] += 1
            sku_daily[date][sku]["qty"] += qty
            sku_daily[date][sku]["amount"] += amt

    # 转普通dict
    out_daily = {}
    for date, d in sorted(daily.items()):
        out_daily[date] = {
            "order_count": d["order_count"],
            "paid": round(d["paid"], 2),
            "refund_full": d["refund_full"],
            "refund_part": d["refund_part"],
            "shops": {s: {"count": v["count"], "paid": round(v["paid"], 2)}
                       for s, v in sorted(d["shops"].items(), key=lambda x: -x[1]["paid"])},
        }
    out_skus = {k: {"name": v["name"], "qty": v["qty"], "amount": round(v["amount"], 2), "orders": v["orders"]}
                for k, v in sorted(skus.items(), key=lambda x: -x[1]["amount"])}
    out_sku_daily = {d: {k: v for k, v in sorted(m.items(), key=lambda x: -x[1]["amount"])}
                      for d, m in sorted(sku_daily.items())}
    return out_daily, out_skus, out_sku_daily, excluded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD（含当天）")
    ap.add_argument("--shop", default="", help="店铺名过滤，如 慕咖；空=全部")
    ap.add_argument("--tag", default="", help="输出文件标签")
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d") + timedelta(days=1)
    # end_time 不能晚于当前时间-2分钟（抓当天数据时截断）
    now = datetime.now() - timedelta(minutes=3)
    if end > now:
        end = now
    if start >= end:
        print("起始时间晚于当前时间，无可拉取数据")
        return

    client = WangdianClient(sid=SID, appkey=APPKEY, appsecret=APPSECRET)
    print(f"拉取 {args.start} ~ {args.end} 订单" + (f"，店铺过滤: {args.shop}" if args.shop else ""), flush=True)

    orders = fetch_range(client, start, end, args.shop or None)
    print(f"共拉到 {len(orders)} 个去重订单", flush=True)

    if not orders:
        print("无数据")
        return

    daily, skus, sku_daily, excluded = summarize(orders, args.start, args.end)
    print(f"拉到 {len(orders)} 单，其中 {excluded} 单归属日期不在范围内（历史修改单），已排除", flush=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.tag or (args.shop or "all")
    out_file = OUTPUT_DIR / f"{args.start}_{args.end}_{tag}.json"
    result = {
        "fetched_at": datetime.now().isoformat(),
        "range": {"start": args.start, "end": args.end},
        "shop_filter": args.shop,
        "total_orders": len(orders),
        "daily": daily,
        "sku_summary": skus,
        "sku_daily": sku_daily,
    }
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"已保存: {out_file}", flush=True)

    # 打印每日摘要
    print("\n=== 每日汇总 ===")
    print(f"{'日期':<12}{'订单数':>6}{'实付':>12}{'全退':>5}{'部分退':>6}")
    for date, d in daily.items():
        print(f"{date:<12}{d['order_count']:>6}{d['paid']:>12,.0f}{d['refund_full']:>5}{d['refund_part']:>6}")


if __name__ == "__main__":
    main()
