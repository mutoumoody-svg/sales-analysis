"""
店铺订单日报服务 — 读取旺店通 trade_query 抓取的每日订单 JSON。

数据源：/opt/sales-analysis/output/trade_daily/*.json
每个 JSON 由 fetch_trade_daily.py 生成，结构：
  - daily: {date: {order_count, paid, refund_full, refund_part, shops: {shop: {count, paid}}}}
  - sku_summary: {sku: {name, qty, amount, orders}}
  - sku_daily: {date: {sku: {qty, amount}}}

服务合并多文件，按日去重（同一天取最新生成的文件）。
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── 数据目录 ──
TRADE_DAILY_DIR = Path("/opt/sales-analysis/output/trade_daily")
REFUND_DAILY_DIR = Path("/opt/sales-analysis/output/refund_daily")


def _load_all_files(shop_filter: str = "") -> dict:
    """扫描目录下所有 JSON，合并 daily 数据，按日去重（取最新 fetched_at）。

    返回 {date: {order_count, paid, refund_full, refund_part, shops, _fetched_at}}
    """
    merged: dict[str, dict] = {}
    if not TRADE_DAILY_DIR.exists():
        return merged
    for f in sorted(TRADE_DAILY_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        # 店铺过滤：文件标签不含 shop_filter 的跳过
        file_shop = data.get("shop_filter") or ""
        if shop_filter and file_shop and shop_filter not in file_shop:
            continue
        fetched = data.get("fetched_at", "")
        daily = data.get("daily", {})
        for date, v in daily.items():
            existing = merged.get(date)
            if existing is None or fetched > existing.get("_fetched_at", ""):
                merged[date] = {**v, "_fetched_at": fetched}
    return merged


def _date_range(days: int, end_date: str | None = None) -> list[str]:
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return [(end - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]


def _load_refund_files() -> dict:
    """扫描退款 JSON，按日去重（取最新 fetched_at）。

    返回 {date: {refund_count, refund_amount, pending_count, pending_amount,
                 shops: {shop: {count, amount}}, _fetched_at}}
    """
    merged: dict[str, dict] = {}
    if not REFUND_DAILY_DIR.exists():
        return merged
    for f in sorted(REFUND_DAILY_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        fetched = data.get("fetched_at", "")
        for date, v in data.get("daily", {}).items():
            existing = merged.get(date)
            if existing is None or fetched > existing.get("_fetched_at", ""):
                merged[date] = {**v, "_fetched_at": fetched}
    return merged


def _refund_for_dates(dates: list[str], shop_filter: str = "") -> dict:
    """汇总日期范围内的退款（可按品牌名过滤店铺）。

    返回 {total_count, total_amount, by_shop: {shop: {count, amount}},
          daily: {date: {count, amount}}}
    """
    merged = _load_refund_files()
    result = {"total_count": 0, "total_amount": 0.0, "by_shop": {}, "daily": {}}
    for date in dates:
        d = merged.get(date)
        if not d:
            continue
        day_count = 0
        day_amount = 0.0
        for shop, sv in d.get("shops", {}).items():
            if shop_filter and shop_filter not in shop:
                continue
            day_count += sv.get("count", 0)
            day_amount += sv.get("amount", 0)
            if shop not in result["by_shop"]:
                result["by_shop"][shop] = {"count": 0, "amount": 0.0}
            result["by_shop"][shop]["count"] += sv.get("count", 0)
            result["by_shop"][shop]["amount"] += sv.get("amount", 0)
        result["daily"][date] = {"count": day_count, "amount": round(day_amount, 2)}
        result["total_count"] += day_count
        result["total_amount"] += day_amount
    result["total_amount"] = round(result["total_amount"], 2)
    return result


def _refund_pending(dates: list[str]) -> float:
    """日期范围内待审退款金额（日级别，无店铺维度，仅供参考）."""
    merged = _load_refund_files()
    return round(sum(merged.get(d, {}).get("pending_amount", 0) for d in dates), 2)


def _get_available_dates(shop_filter: str = "") -> list[str]:
    """列出所有可用日期."""
    merged = _load_all_files(shop_filter)
    return sorted(merged.keys())


def get_overview(days: int = 7, shop_filter: str = "") -> dict:
    """概览：最近 N 天汇总 + 今天/昨天对比 + 店铺分布."""
    merged = _load_all_files(shop_filter)
    dates = _date_range(days)
    today = dates[-1] if dates else ""
    yesterday = dates[-2] if len(dates) >= 2 else ""

    total_cnt = 0
    total_paid = 0.0
    shop_agg: dict[str, dict] = {}
    today_data = merged.get(today, {})
    yesterday_data = merged.get(yesterday, {})

    for date in dates:
        d = merged.get(date)
        if not d:
            continue
        total_cnt += d.get("order_count", 0)
        total_paid += d.get("paid", 0)
        for shop, sv in d.get("shops", {}).items():
            if shop not in shop_agg:
                shop_agg[shop] = {"count": 0, "paid": 0.0}
            shop_agg[shop]["count"] += sv.get("count", 0)
            shop_agg[shop]["paid"] += sv.get("paid", 0)

    actual_days = sum(1 for d in dates if d in merged)
    avg_paid = total_paid / actual_days if actual_days else 0

    # 退款（按品牌过滤店铺）
    refund = _refund_for_dates(dates, shop_filter)
    total_refund = refund["total_amount"]
    net_paid = total_paid - total_refund

    today_paid = today_data.get("paid", 0)
    yesterday_paid = yesterday_data.get("paid", 0)
    dod = 0.0
    if yesterday_paid > 0:
        dod = (today_paid - yesterday_paid) / yesterday_paid * 100

    today_refund = refund["daily"].get(today, {}).get("amount", 0)
    yesterday_refund = refund["daily"].get(yesterday, {}).get("amount", 0)

    return {
        "range": {"start": dates[0] if dates else "", "end": today, "days": days},
        "total_orders": total_cnt,
        "total_paid": round(total_paid, 2),
        "total_refund": round(total_refund, 2),
        "net_paid": round(net_paid, 2),
        "refund_rate": round(total_refund / total_paid * 100, 1) if total_paid else 0,
        "refund_count": refund["total_count"],
        "avg_daily_paid": round(avg_paid, 2),
        "avg_daily_net": round(net_paid / actual_days, 2) if actual_days else 0,
        "avg_order_value": round(total_paid / total_cnt, 2) if total_cnt else 0,
        "active_days": actual_days,
        "today": {"date": today, "orders": today_data.get("order_count", 0),
                  "paid": round(today_paid, 2),
                  "refund": round(today_refund, 2),
                  "net": round(today_paid - today_refund, 2)},
        "yesterday": {"date": yesterday, "orders": yesterday_data.get("order_count", 0),
                      "paid": round(yesterday_paid, 2),
                      "refund": round(yesterday_refund, 2),
                      "net": round(yesterday_paid - yesterday_refund, 2)},
        "dod_pct": round(dod, 1),
        "shops": [
            {"shop": s, "count": v["count"], "paid": round(v["paid"], 2),
             "paid_pct": round(v["paid"] / total_paid * 100, 1) if total_paid else 0,
             "refund": round(refund["by_shop"].get(s, {}).get("amount", 0), 2),
             "net": round(v["paid"] - refund["by_shop"].get(s, {}).get("amount", 0), 2),
             "avg_order": round(v["paid"] / v["count"], 2) if v["count"] else 0}
            for s, v in sorted(shop_agg.items(), key=lambda x: -x[1]["paid"])
        ],
    }


def get_trend(days: int = 30, shop_filter: str = "") -> list[dict]:
    """每日趋势."""
    merged = _load_all_files(shop_filter)
    dates = _date_range(days)
    refund = _refund_for_dates(dates, shop_filter)
    prev_paid = None
    result = []
    for date in dates:
        d = merged.get(date)
        paid = d.get("paid", 0) if d else 0
        orders = d.get("order_count", 0) if d else 0
        r_amt = refund["daily"].get(date, {}).get("amount", 0)
        dod = None
        if prev_paid is not None and prev_paid > 0:
            dod = round((paid - prev_paid) / prev_paid * 100, 1)
        result.append({
            "date": date,
            "orders": orders,
            "paid": round(paid, 2),
            "refund": round(r_amt, 2),
            "net": round(paid - r_amt, 2),
            "refund_count": refund["daily"].get(date, {}).get("count", 0),
            "dod_pct": dod,
            "refund_full": d.get("refund_full", 0) if d else 0,
            "refund_part": d.get("refund_part", 0) if d else 0,
        })
        prev_paid = paid if paid > 0 else prev_paid
    return result


def get_by_shop(days: int = 7, shop_filter: str = "") -> list[dict]:
    """按店铺汇总."""
    merged = _load_all_files(shop_filter)
    dates = _date_range(days)
    refund = _refund_for_dates(dates, shop_filter)
    shop_agg: dict[str, dict] = {}
    for date in dates:
        d = merged.get(date)
        if not d:
            continue
        for shop, sv in d.get("shops", {}).items():
            if shop not in shop_agg:
                shop_agg[shop] = {"count": 0, "paid": 0.0, "days": 0}
            shop_agg[shop]["count"] += sv.get("count", 0)
            shop_agg[shop]["paid"] += sv.get("paid", 0)
            shop_agg[shop]["days"] += 1
    total_paid = sum(v["paid"] for v in shop_agg.values())
    return [
        {"shop": s, "count": v["count"], "paid": round(v["paid"], 2),
         "paid_pct": round(v["paid"] / total_paid * 100, 1) if total_paid else 0,
         "refund": round(refund["by_shop"].get(s, {}).get("amount", 0), 2),
         "net": round(v["paid"] - refund["by_shop"].get(s, {}).get("amount", 0), 2),
         "refund_rate": round(refund["by_shop"].get(s, {}).get("amount", 0) / v["paid"] * 100, 1) if v["paid"] else 0,
         "avg_order": round(v["paid"] / v["count"], 2) if v["count"] else 0,
         "active_days": v["days"]}
        for s, v in sorted(shop_agg.items(), key=lambda x: -x[1]["paid"])
    ]


def get_top_skus(days: int = 30, shop_filter: str = "", limit: int = 20) -> list[dict]:
    """Top SKU 排行（按实付金额）."""
    merged = _load_all_files(shop_filter)
    dates = set(_date_range(days))
    sku_agg: dict[str, dict] = {}
    # 需要从原始文件读 sku_daily
    if TRADE_DAILY_DIR.exists():
        for f in sorted(TRADE_DAILY_DIR.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
            file_shop = data.get("shop_filter") or ""
            if shop_filter and file_shop and shop_filter not in file_shop:
                continue
            sku_daily = data.get("sku_daily", {})
            for date, skus in sku_daily.items():
                if date not in dates:
                    continue
                for sku, v in skus.items():
                    if sku not in sku_agg:
                        sku_agg[sku] = {"name": "", "qty": 0, "amount": 0.0, "orders": 0}
                    sku_agg[sku]["qty"] += v.get("qty", 0)
                    sku_agg[sku]["amount"] += v.get("amount", 0)
                    sku_agg[sku]["orders"] += 1
    return [
        {"sku": k, "name": v["name"], "qty": v["qty"], "amount": round(v["amount"], 2),
         "avg_price": round(v["amount"] / v["qty"], 2) if v["qty"] else 0,
         "orders": v["orders"]}
        for k, v in sorted(sku_agg.items(), key=lambda x: -x[1]["amount"])[:limit]
    ]


def get_daily_detail(date: str, shop_filter: str = "") -> dict:
    """某日明细."""
    merged = _load_all_files(shop_filter)
    d = merged.get(date)
    if not d:
        return {"date": date, "found": False}
    refund = _refund_for_dates([date], shop_filter)
    refund_amt = refund["total_amount"]
    paid = d.get("paid", 0)
    # 合并退款店铺到明细
    shop_detail: dict[str, dict] = {}
    for s, v in d.get("shops", {}).items():
        shop_detail[s] = {"count": v.get("count", 0), "paid": v.get("paid", 0),
                          "refund": refund["by_shop"].get(s, {}).get("amount", 0)}
    for s, v in refund["by_shop"].items():
        if s not in shop_detail:
            shop_detail[s] = {"count": 0, "paid": 0, "refund": v.get("amount", 0)}
    return {
        "date": date,
        "found": True,
        "order_count": d.get("order_count", 0),
        "paid": round(paid, 2),
        "refund": round(refund_amt, 2),
        "refund_count": refund["total_count"],
        "net": round(paid - refund_amt, 2),
        "refund_full": d.get("refund_full", 0),
        "refund_part": d.get("refund_part", 0),
        "shops": [
            {"shop": s, "count": v["count"], "paid": round(v["paid"], 2),
             "refund": round(v["refund"], 2),
             "net": round(v["paid"] - v["refund"], 2)}
            for s, v in sorted(shop_detail.items(), key=lambda x: -(x[1]["paid"] - x[1]["refund"]))
        ],
    }
