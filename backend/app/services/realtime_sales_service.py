"""
实时销售分析服务 — 读取 kucun 系统的每日出库 JSON 数据。

数据源：/opt/kucun/output/daily_outbound/YYYY-MM-DD.json
每个 JSON 包含：
  - total_orders / total_quantity / total_sell_amount / total_cost_amount
  - order_level_receivable / order_level_goods_amount
  - details[]: spec_no, goods_name, quantity, total_sell_amount, total_cost_amount,
               avg_sell_price, avg_cost_price, order_count, shops[], warehouses[]

成本口径：系统成本优先。所有毛利计算使用 products.unit_cost（系统内维护的成本），
旺店通出库单自带的 cost_price 仅作为 SKU 无系统成本时的回退，并在 cost_source 标记。
"""

import json
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.core.config import settings


# ── 数据目录 ──
DAILY_OUTBOUND_DIR = Path(getattr(settings, "KUCUN_OUTPUT_PATH", "/opt/kucun/output")) / "daily_outbound"

# ── 系统成本缓存（products.unit_cost）──
_COST_CACHE_TTL = 600  # 秒
_cost_cache: Optional[dict] = None
_cost_cache_ts: float = 0.0


def _load_system_costs() -> dict:
    """加载系统成本表 {sku: unit_cost}，带10分钟缓存。DB 异常时返回上次缓存。"""
    global _cost_cache, _cost_cache_ts
    now = time.time()
    if _cost_cache is not None and now - _cost_cache_ts < _COST_CACHE_TTL:
        return _cost_cache
    costs: dict = {}
    try:
        from app.database import SessionLocal
        from app.models.product import Product

        db = SessionLocal()
        try:
            rows = db.query(Product.sku, Product.unit_cost).filter(Product.unit_cost > 0).all()
            costs = {sku: float(uc) for sku, uc in rows if sku}
        finally:
            db.close()
    except Exception:
        costs = _cost_cache or {}
    _cost_cache = costs
    _cost_cache_ts = now
    return costs


def _apply_system_cost(data: dict) -> dict:
    """用系统成本覆盖出库单里的旺店通成本。

    - 有系统成本的 SKU：total_cost_amount = unit_cost × quantity
    - 无系统成本的 SKU：保留旺店通成本，cost_source='wdt'（回退）
    - 日级 total_cost_amount 按明细重算
    """
    costs = _load_system_costs()
    missing: set = set()
    total_cost = 0.0
    for item in data.get("details", []):
        qty = item.get("quantity", 0) or 0
        uc = costs.get(item.get("spec_no", ""))
        if uc is not None:
            c = round(uc * qty, 2)
            item["total_cost_amount"] = c
            item["avg_cost_price"] = round(c / qty, 4) if qty else 0.0
            item["cost_source"] = "system"
        else:
            missing.add(item.get("spec_no", ""))
            item["cost_source"] = "wdt"
        total_cost += item.get("total_cost_amount", 0) or 0
    data["total_cost_amount"] = round(total_cost, 2)
    data["cost_missing_skus"] = sorted(missing)
    return data


def _load_daily_json(date_str: str) -> Optional[dict]:
    """加载某一天的出库 JSON（应用系统成本覆盖），不存在返回 None。"""
    filepath = DAILY_OUTBOUND_DIR / f"{date_str}.json"
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _apply_system_cost(data)
    except (json.JSONDecodeError, OSError):
        return None


def _date_range(days: int, end_date: str | None = None) -> list[str]:
    """生成最近 N 天的日期列表（含 end_date，默认今天）。"""
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return [(end - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]


def _get_available_dates() -> list[str]:
    """列出 daily_outbound 目录下所有可用的日期。"""
    if not DAILY_OUTBOUND_DIR.exists():
        return []
    dates = []
    for f in DAILY_OUTBOUND_DIR.glob("*.json"):
        date_str = f.stem
        # 只保留 YYYY-MM-DD 格式且年份 >= 2024
        if len(date_str) == 10 and date_str[4] == "-" and date_str[:4] >= "2024":
            dates.append(date_str)
    return sorted(dates)


def get_overview(days: int = 7) -> dict:
    """
    获取最近 N 天的销售概览。

    返回：
      - today: 今天的销售数据
      - yesterday: 昨天的销售数据
      - period: 最近 N 天汇总
      - period_daily: 每日明细列表
      - available_dates: 可用日期列表
      - latest_date: 最新有数据的日期
    """
    dates = _date_range(days)
    available = _get_available_dates()
    latest_date = available[-1] if available else None

    period_total = {
        "orders": 0,
        "quantity": 0.0,
        "sell_amount": 0.0,
        "cost_amount": 0.0,
        "receivable": 0.0,
        "goods_amount": 0.0,
    }
    period_daily = []

    for d in dates:
        data = _load_daily_json(d)
        if data is None:
            period_daily.append({
                "date": d,
                "orders": 0, "quantity": 0,
                "sell_amount": 0, "cost_amount": 0,
                "gross_profit": 0, "margin_pct": 0,
                "receivable": 0, "goods_amount": 0,
                "has_data": False,
            })
            continue

        sell = data.get("total_sell_amount", 0)
        cost = data.get("total_cost_amount", 0)
        gross = sell - cost
        margin = round(gross / sell * 100, 2) if sell > 0 else 0

        period_daily.append({
            "date": d,
            "orders": data.get("total_orders", 0),
            "quantity": data.get("total_quantity", 0),
            "sell_amount": round(sell, 2),
            "cost_amount": round(cost, 2),
            "gross_profit": round(gross, 2),
            "margin_pct": margin,
            "receivable": data.get("order_level_receivable", 0),
            "goods_amount": data.get("order_level_goods_amount", 0),
            "has_data": True,
        })

        period_total["orders"] += data.get("total_orders", 0)
        period_total["quantity"] += data.get("total_quantity", 0)
        period_total["sell_amount"] += sell
        period_total["cost_amount"] += cost
        period_total["receivable"] += data.get("order_level_receivable", 0)
        period_total["goods_amount"] += data.get("order_level_goods_amount", 0)

    period_total["gross_profit"] = round(period_total["sell_amount"] - period_total["cost_amount"], 2)
    period_total["margin_pct"] = (
        round(period_total["gross_profit"] / period_total["sell_amount"] * 100, 2)
        if period_total["sell_amount"] > 0 else 0
    )
    for k in ["sell_amount", "cost_amount", "receivable", "goods_amount"]:
        period_total[k] = round(period_total[k], 2)
    period_total["quantity"] = round(period_total["quantity"], 2)
    period_total["avg_daily_orders"] = round(period_total["orders"] / days, 1)
    period_total["avg_daily_sell"] = round(period_total["sell_amount"] / days, 2)

    # 今天和昨天
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    today_data = _load_daily_json(today_str)
    yesterday_data = _load_daily_json(yesterday_str)

    # 汇总期间内缺系统成本的 SKU（回退用了旺店通成本，需在系统里补录）
    period_missing: set = set()
    for d in dates:
        data = _load_daily_json(d)
        if data:
            period_missing.update(data.get("cost_missing_skus", []))

    def _summary(data, date_str):
        if not data:
            return {"date": date_str, "orders": 0, "quantity": 0,
                    "sell_amount": 0, "cost_amount": 0, "gross_profit": 0,
                    "margin_pct": 0, "has_data": False}
        sell = data.get("total_sell_amount", 0)
        cost = data.get("total_cost_amount", 0)
        gross = sell - cost
        return {
            "date": date_str,
            "orders": data.get("total_orders", 0),
            "quantity": data.get("total_quantity", 0),
            "sell_amount": round(sell, 2),
            "cost_amount": round(cost, 2),
            "gross_profit": round(gross, 2),
            "margin_pct": round(gross / sell * 100, 2) if sell > 0 else 0,
            "receivable": data.get("order_level_receivable", 0),
            "has_data": True,
        }

    return {
        "today": _summary(today_data, today_str),
        "yesterday": _summary(yesterday_data, yesterday_str),
        "period": period_total,
        "period_daily": period_daily,
        "available_dates": available[-30:] if available else [],
        "latest_date": latest_date,
        "days": days,
        "cost_missing_skus": sorted(period_missing),
    }


def get_trend(days: int = 30) -> list[dict]:
    """获取最近 N 天的每日趋势数据。"""
    dates = _date_range(days)
    trend = []
    for d in dates:
        data = _load_daily_json(d)
        if data is None:
            trend.append({
                "date": d, "orders": 0, "quantity": 0,
                "sell_amount": 0, "cost_amount": 0,
                "gross_profit": 0, "margin_pct": 0,
            })
            continue
        sell = data.get("total_sell_amount", 0)
        cost = data.get("total_cost_amount", 0)
        gross = sell - cost
        trend.append({
            "date": d,
            "orders": data.get("total_orders", 0),
            "quantity": data.get("total_quantity", 0),
            "sell_amount": round(sell, 2),
            "cost_amount": round(cost, 2),
            "gross_profit": round(gross, 2),
            "margin_pct": round(gross / sell * 100, 2) if sell > 0 else 0,
        })
    return trend


def get_top_skus(days: int = 7, limit: int = 20) -> list[dict]:
    """获取最近 N 天 Top SKU（按销售额排序）。"""
    dates = _date_range(days)
    sku_agg: dict[str, dict] = {}

    for d in dates:
        data = _load_daily_json(d)
        if data is None:
            continue
        for item in data.get("details", []):
            spec_no = item.get("spec_no", "")
            if not spec_no:
                continue
            if spec_no not in sku_agg:
                sku_agg[spec_no] = {
                    "spec_no": spec_no,
                    "goods_name": item.get("goods_name", ""),
                    "quantity": 0.0,
                    "sell_amount": 0.0,
                    "cost_amount": 0.0,
                    "order_count": 0,
                    "shops": set(),
                    "warehouses": set(),
                    "days_sold": 0,
                }
            agg = sku_agg[spec_no]
            agg["quantity"] += item.get("quantity", 0)
            agg["sell_amount"] += item.get("total_sell_amount", 0)
            agg["cost_amount"] += item.get("total_cost_amount", 0)
            agg["order_count"] += item.get("order_count", 0)
            agg["days_sold"] += 1
            for s in item.get("shops", []):
                agg["shops"].add(s)
            for w in item.get("warehouses", []):
                agg["warehouses"].add(w)

    # 转为列表并排序
    result = []
    for agg in sku_agg.values():
        sell = round(agg["sell_amount"], 2)
        cost = round(agg["cost_amount"], 2)
        result.append({
            "spec_no": agg["spec_no"],
            "goods_name": agg["goods_name"],
            "quantity": round(agg["quantity"], 2),
            "sell_amount": sell,
            "cost_amount": cost,
            "gross_profit": round(sell - cost, 2),
            "margin_pct": round((sell - cost) / sell * 100, 2) if sell > 0 else 0,
            "order_count": agg["order_count"],
            "days_sold": agg["days_sold"],
            "shop_count": len(agg["shops"]),
            "shops": sorted(agg["shops"]),
            "warehouses": sorted(agg["warehouses"]),
        })

    # 按销售额降序
    result.sort(key=lambda x: x["sell_amount"], reverse=True)
    return result[:limit]


def get_by_shop(days: int = 7) -> list[dict]:
    """按店铺汇总最近 N 天的销售数据。"""
    dates = _date_range(days)
    shop_agg: dict[str, dict] = {}

    for d in dates:
        data = _load_daily_json(d)
        if data is None:
            continue
        for item in data.get("details", []):
            sell = item.get("total_sell_amount", 0)
            cost = item.get("total_cost_amount", 0)
            qty = item.get("quantity", 0)
            orders = item.get("order_count", 0)
            for shop in item.get("shops", []):
                if shop not in shop_agg:
                    shop_agg[shop] = {
                        "shop": shop,
                        "quantity": 0.0,
                        "sell_amount": 0.0,
                        "cost_amount": 0.0,
                        "order_count": 0,
                        "sku_count": set(),
                    }
                agg = shop_agg[shop]
                # 注意：一个 SKU 可能在多店铺出现，这里按 shop 均分
                shop_count = len(item.get("shops", []))
                if shop_count > 0:
                    agg["quantity"] += qty / shop_count
                    agg["sell_amount"] += sell / shop_count
                    agg["cost_amount"] += cost / shop_count
                    agg["order_count"] += orders / shop_count
                agg["sku_count"].add(item.get("spec_no", ""))

    result = []
    for agg in shop_agg.values():
        sell = round(agg["sell_amount"], 2)
        cost = round(agg["cost_amount"], 2)
        result.append({
            "shop": agg["shop"],
            "quantity": round(agg["quantity"], 2),
            "sell_amount": sell,
            "cost_amount": cost,
            "gross_profit": round(sell - cost, 2),
            "margin_pct": round((sell - cost) / sell * 100, 2) if sell > 0 else 0,
            "order_count": round(agg["order_count"]),
            "sku_count": len(agg["sku_count"]),
        })
    result.sort(key=lambda x: x["sell_amount"], reverse=True)
    return result


def get_by_warehouse(days: int = 7) -> list[dict]:
    """按仓库汇总最近 N 天的销售数据。"""
    dates = _date_range(days)
    wh_agg: dict[str, dict] = {}

    for d in dates:
        data = _load_daily_json(d)
        if data is None:
            continue
        for item in data.get("details", []):
            sell = item.get("total_sell_amount", 0)
            cost = item.get("total_cost_amount", 0)
            qty = item.get("quantity", 0)
            orders = item.get("order_count", 0)
            for wh in item.get("warehouses", []):
                if wh not in wh_agg:
                    wh_agg[wh] = {
                        "warehouse": wh,
                        "quantity": 0.0,
                        "sell_amount": 0.0,
                        "cost_amount": 0.0,
                        "order_count": 0,
                        "sku_count": set(),
                    }
                agg = wh_agg[wh]
                wh_count = len(item.get("warehouses", []))
                if wh_count > 0:
                    agg["quantity"] += qty / wh_count
                    agg["sell_amount"] += sell / wh_count
                    agg["cost_amount"] += cost / wh_count
                    agg["order_count"] += orders / wh_count
                agg["sku_count"].add(item.get("spec_no", ""))

    result = []
    for agg in wh_agg.values():
        sell = round(agg["sell_amount"], 2)
        cost = round(agg["cost_amount"], 2)
        result.append({
            "warehouse": agg["warehouse"],
            "quantity": round(agg["quantity"], 2),
            "sell_amount": sell,
            "cost_amount": cost,
            "gross_profit": round(sell - cost, 2),
            "margin_pct": round((sell - cost) / sell * 100, 2) if sell > 0 else 0,
            "order_count": round(agg["order_count"]),
            "sku_count": len(agg["sku_count"]),
        })
    result.sort(key=lambda x: x["sell_amount"], reverse=True)
    return result


def get_daily_detail(date_str: str) -> dict:
    """获取某一天的详细出库数据（SKU 明细）。"""
    data = _load_daily_json(date_str)
    if data is None:
        return {"date": date_str, "has_data": False, "details": [],
                "total_orders": 0, "total_quantity": 0,
                "total_sell_amount": 0, "total_cost_amount": 0}

    details = data.get("details", [])
    # 按 sell_amount 降序
    details.sort(key=lambda x: x.get("total_sell_amount", 0), reverse=True)

    return {
        "date": date_str,
        "has_data": True,
        "fetch_time": data.get("fetch_time", ""),
        "total_orders": data.get("total_orders", 0),
        "total_quantity": data.get("total_quantity", 0),
        "total_sell_amount": data.get("total_sell_amount", 0),
        "total_cost_amount": data.get("total_cost_amount", 0),
        "order_level_receivable": data.get("order_level_receivable", 0),
        "order_level_goods_amount": data.get("order_level_goods_amount", 0),
        "skipped_sku": data.get("skipped_sku", 0),
        "skipped_wh": data.get("skipped_wh", 0),
        "cost_missing_skus": data.get("cost_missing_skus", []),
        "details": details,
    }


def get_monthly_summary() -> list[dict]:
    """按月汇总销售额（从 daily_outbound 数据聚合）。"""
    available = _get_available_dates()
    if not available:
        return []

    monthly: dict[str, dict] = {}
    for d in available:
        month = d[:7]  # YYYY-MM
        data = _load_daily_json(d)
        if data is None:
            continue
        if month not in monthly:
            monthly[month] = {
                "month": month,
                "orders": 0,
                "quantity": 0.0,
                "sell_amount": 0.0,
                "cost_amount": 0.0,
                "receivable": 0.0,
                "days_with_data": 0,
            }
        m = monthly[month]
        m["orders"] += data.get("total_orders", 0)
        m["quantity"] += data.get("total_quantity", 0)
        m["sell_amount"] += data.get("total_sell_amount", 0)
        m["cost_amount"] += data.get("total_cost_amount", 0)
        m["receivable"] += data.get("order_level_receivable", 0)
        m["days_with_data"] += 1

    result = []
    for m in monthly.values():
        sell = round(m["sell_amount"], 2)
        cost = round(m["cost_amount"], 2)
        result.append({
            "month": m["month"],
            "orders": m["orders"],
            "quantity": round(m["quantity"], 2),
            "sell_amount": sell,
            "cost_amount": cost,
            "gross_profit": round(sell - cost, 2),
            "margin_pct": round((sell - cost) / sell * 100, 2) if sell > 0 else 0,
            "receivable": round(m["receivable"], 2),
            "days_with_data": m["days_with_data"],
            "avg_daily_sell": round(sell / m["days_with_data"], 2) if m["days_with_data"] > 0 else 0,
        })
    result.sort(key=lambda x: x["month"])
    return result
