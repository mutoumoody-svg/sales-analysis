"""
Reorder Service - 统一补货建议引擎.

基于近6个月加权日均销量 + 当前库存，计算补货建议。

核心参数:
- 采购周期：60天（2个月）
- 加权月数：6个月（越近权重越高）
- 安全系数：周转<2个月 → 1.7（快消品需更多缓冲）；周转≥2个月 → 1.3（慢销品缓冲较少）

公式:
- 加权日均 = Σ(各月日均 × 权重) / Σ权重，权重 = [6, 5, 4, 3, 2, 1]
- 周转天数 = 当前可售库存 / 加权日均
- 安全库存 = 加权日均 × 采购周期 × 安全系数
- 补货量 = max(安全库存 + 采购周期需求 - 有效库存, 采购周期需求)
"""

from typing import Dict, List, Optional
from datetime import date
from collections import defaultdict
import calendar

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.inventory import Inventory
from app.models.product import Product
from app.models.sales_summary import SalesSummary
from app.models.order import Order, OrderItem
from app.utils.period import resolve_period, period_to_date_range


# ===== 核心常量 =====
PROCUREMENT_DAYS = 60            # 采购周期：2个月
WEIGHTED_MONTHS = 6              # 加权月数
MONTH_WEIGHTS = [6, 5, 4, 3, 2, 1]  # 加权权重：越近越高
SAFETY_FACTOR_FAST = 1.7         # 周转<2个月（快消品）
SAFETY_FACTOR_SLOW = 1.3         # 周转≥2个月（慢销品）
TURNOVER_THRESHOLD_DAYS = 60     # 周转阈值：2个月
# 滞销判定
STALE_STOCK_THRESHOLD = 50       # 库存>50件
STALE_SALES_THRESHOLD = 10       # 近6个月总销量<10件


def _get_recent_periods(period: str, count: int = WEIGHTED_MONTHS) -> List[str]:
    """从指定月份向前推 N 个月，返回 YYYY-MM 列表（最近在前）."""
    year, month = int(period[:4]), int(period[5:7])
    periods = []
    for i in range(count):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        periods.append(f"{y:04d}-{m:02d}")
    return periods


def _days_in_month(period: str) -> int:
    """获取该月天数."""
    year, month = int(period[:4]), int(period[5:7])
    return calendar.monthrange(year, month)[1]


def calculate_reorder(
    db: Session,
    period: str,
    brand: Optional[str] = None,
    warehouse: Optional[str] = None,
) -> Dict:
    """统一补货建议计算引擎.

    Args:
        db: 数据库会话
        period: 当前月份 YYYY-MM
        brand: 品牌筛选
        warehouse: 仓库筛选

    Returns:
        {
            "summary": {...},
            "items": [...],
        }
    """
    # 1. 获取近4个月月份列表
    periods = _get_recent_periods(period, WEIGHTED_MONTHS)

    # 2. 查询各月各商品销量
    sales_query = (
        db.query(
            SalesSummary.product_id,
            SalesSummary.period,
            func.sum(SalesSummary.net_qty).label("qty"),
            func.sum(SalesSummary.net_amount).label("revenue"),
        )
        .filter(SalesSummary.period.in_(periods))
        .group_by(SalesSummary.product_id, SalesSummary.period)
    )
    if brand:
        sales_query = sales_query.join(
            Product, SalesSummary.product_id == Product.id
        ).filter(Product.brand == brand)
    sales_rows = sales_query.all()

    # 构建 {product_id_str: {period: {qty, revenue}}} 映射
    sales_map: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
    for r in sales_rows:
        sales_map[str(r.product_id)][r.period] = {
            "qty": int(r.qty) if r.qty else 0,
            "revenue": float(r.revenue) if r.revenue else 0,
        }

    # 3. 获取当前库存（最新快照）
    latest_inv_date = db.query(func.max(Inventory.date)).scalar()
    if not latest_inv_date:
        return {
            "summary": {
                "total_skus": 0,
                "reorder_count": 0,
                "urgent_count": 0,
                "normal_count": 0,
                "planned_count": 0,
                "total_reorder_qty": 0,
                "total_reorder_value": 0,
                "fast_moving_count": 0,
                "slow_moving_count": 0,
                "periods": periods,
                "procurement_days": PROCUREMENT_DAYS,
                "weighted_months": WEIGHTED_MONTHS,
                "month_weights": MONTH_WEIGHTS,
                "safety_factor_fast": SAFETY_FACTOR_FAST,
                "safety_factor_slow": SAFETY_FACTOR_SLOW,
                "turnover_threshold_days": TURNOVER_THRESHOLD_DAYS,
            },
            "items": [],
            "error": "No inventory data",
        }

    inv_query = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.brand,
            Product.unit_cost,
            # 跨仓库汇总库存（避免补货量按仓库重复计算）
            func.sum(Inventory.available_qty).label("available"),
            func.sum(Inventory.reserved_qty).label("reserved"),
            func.sum(Inventory.inbound_qty).label("inbound"),
            # 涉及仓库数（用于展示）
            func.count(func.distinct(Inventory.warehouse)).label("warehouse_count"),
            func.max(Inventory.warehouse).label("warehouse"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .filter(Inventory.date == latest_inv_date)
    )
    if brand:
        inv_query = inv_query.filter(Product.brand == brand)
    if warehouse:
        inv_query = inv_query.filter(Inventory.warehouse == warehouse)
    # 按 SKU 聚合（不按仓库）— 补货决策是 SKU 级别的
    inv_query = inv_query.group_by(
        Product.id,
        Product.sku,
        Product.product_name,
        Product.brand,
        Product.unit_cost,
    )
    inv_results = inv_query.all()

    # 4. 获取每个商品最后销售日期（当前月份范围内）
    p_start, p_end = period_to_date_range(period)
    last_sale_query = (
        db.query(
            OrderItem.product_id,
            func.max(Order.order_date).label("last_sale_date"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(
            Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
            Order.order_date >= p_start,
            Order.order_date <= p_end,
        )
        .group_by(OrderItem.product_id)
    )
    last_sale_map = {
        str(r.product_id): r.last_sale_date for r in last_sale_query.all()
    }

    # 5. 组装分析数据
    items = []
    urgent_count = 0
    normal_count = 0
    planned_count = 0
    total_reorder_qty = 0
    total_reorder_value = 0.0
    total_capital = 0.0
    turnover_days_list = []
    stale_count = 0

    for r in inv_results:
        available = int(r.available) if r.available else 0
        reserved = int(r.reserved) if r.reserved else 0
        inbound = int(r.inbound) if r.inbound else 0
        effective = available + inbound - reserved
        unit_cost = float(r.unit_cost) if r.unit_cost else 0
        pid = str(r.product_id)

        # --- 计算加权日均销量 ---
        product_sales = sales_map.get(pid, {})
        weighted_sum = 0.0
        weight_total = 0
        monthly_data = []

        for i, p in enumerate(periods):
            month_info = product_sales.get(p, {"qty": 0, "revenue": 0})
            qty = month_info["qty"]
            days = _days_in_month(p)
            daily_rate = qty / days if days > 0 and qty > 0 else 0
            weight = MONTH_WEIGHTS[i] if i < len(MONTH_WEIGHTS) else 1
            weighted_sum += daily_rate * weight
            weight_total += weight
            monthly_data.append({
                "period": p,
                "qty": qty,
                "daily_rate": round(daily_rate, 2),
                "weight": weight,
            })

        weighted_daily = weighted_sum / weight_total if weight_total > 0 else 0

        # 4个月总销量
        total_sold_qty = sum(m["qty"] for m in monthly_data)

        # --- 周转天数 ---
        if weighted_daily > 0:
            turnover_days = round(available / weighted_daily, 1)
            turnover_days_list.append(turnover_days)
        else:
            turnover_days = None

        # --- 确定安全系数 ---
        if turnover_days is not None and turnover_days < TURNOVER_THRESHOLD_DAYS:
            safety_factor = SAFETY_FACTOR_FAST
            turnover_category = "fast"
        else:
            safety_factor = SAFETY_FACTOR_SLOW
            turnover_category = "slow"

        # --- 安全库存 ---
        safety_stock = max(int(weighted_daily * PROCUREMENT_DAYS * safety_factor), 0)

        # --- 采购周期需求 ---
        cycle_demand = int(weighted_daily * PROCUREMENT_DAYS)

        # --- 补货量 ---
        reorder_qty = max(safety_stock + cycle_demand - effective, cycle_demand)

        # 是否需要补货（有效库存低于安全库存）
        needs_reorder = reorder_qty > 0 and effective < safety_stock

        # --- 优先级 ---
        days_of_supply = int(effective / weighted_daily) if weighted_daily > 0 else None

        if needs_reorder:
            if days_of_supply is not None and days_of_supply < 7:
                priority = "urgent"
                urgent_count += 1
            elif days_of_supply is not None and days_of_supply < PROCUREMENT_DAYS:
                priority = "normal"
                normal_count += 1
            else:
                priority = "planned"
                planned_count += 1
        else:
            priority = "none"

        if needs_reorder:
            total_reorder_qty += reorder_qty
            reorder_value = reorder_qty * unit_cost
            total_reorder_value += reorder_value
        else:
            reorder_value = 0
            reorder_qty = 0

        # --- 趋势分析 ---
        recent_qty = monthly_data[0]["qty"] if monthly_data else 0
        older_qtys = [m["qty"] for m in monthly_data[1:]]
        older_avg = sum(older_qtys) / len(older_qtys) if older_qtys else 0
        if older_avg > 0:
            trend_pct = round((recent_qty - older_avg) / older_avg * 100, 1)
        elif recent_qty > 0:
            trend_pct = 100.0
        else:
            trend_pct = 0.0

        # --- 滞销判定 ---
        last_sale = last_sale_map.get(pid)
        today = p_end
        if last_sale:
            stale_days = (today - last_sale).days
        else:
            stale_days = None

        is_stale = (
            (stale_days is not None and stale_days >= 30 and available > 0)
            or (stale_days is None and available > 0 and total_sold_qty == 0)
            or (available > STALE_STOCK_THRESHOLD and total_sold_qty < STALE_SALES_THRESHOLD)
        )
        if is_stale:
            stale_count += 1

        # --- 资金占用 ---
        capital_occupied = available * unit_cost
        total_capital += capital_occupied

        # --- 综合状态 ---
        if available == 0 and inbound == 0:
            status = "stockout"
        elif is_stale:
            status = "stale"
        elif needs_reorder:
            status = "reorder"
        elif safety_stock > 0 and available > safety_stock * 3:
            status = "overstock"
        else:
            status = "healthy"

        items.append({
            "product_id": pid,
            "sku": r.sku,
            "product_name": r.product_name,
            "brand": r.brand,
            # 补货按 SKU 级别聚合，仓库维度改为"全部仓库"或单仓库筛选
            "warehouse": f"全部仓库({int(r.warehouse_count)}个)" if r.warehouse_count > 1 else r.warehouse,
            "available_qty": available,
            "reserved_qty": reserved,
            "inbound_qty": inbound,
            "effective_qty": effective,
            "unit_cost": unit_cost,
            "capital_occupied": round(capital_occupied, 2),
            # 多月销量数据
            "monthly_sales": monthly_data,
            "weighted_daily_rate": round(weighted_daily, 2),
            "trend_pct": trend_pct,
            "trend_direction": "up" if trend_pct > 10 else ("down" if trend_pct < -10 else "stable"),
            # 周转与安全库存
            "turnover_days": turnover_days,
            "turnover_category": turnover_category,
            "safety_factor": safety_factor,
            "safety_stock": safety_stock,
            "cycle_demand": cycle_demand,
            "reorder_qty": reorder_qty,
            "reorder_value": round(reorder_value, 2),
            "needs_reorder": needs_reorder,
            "priority": priority,
            "days_of_supply": days_of_supply,
            # 旧字段兼容
            "daily_rate": round(weighted_daily, 2),
            "total_sold_qty": total_sold_qty,
            "last_sale_date": last_sale.isoformat() if last_sale else None,
            "stale_days": stale_days,
            "is_stale": is_stale,
            "status": status,
        })

    # 排序：需补货的在前，按优先级和补货金额排序
    priority_order = {"urgent": 0, "normal": 1, "planned": 2, "none": 3}
    items.sort(
        key=lambda x: (
            priority_order.get(x.get("priority", "none"), 3),
            -x.get("reorder_value", 0),
        )
    )

    # 统计
    reorder_items = [i for i in items if i["needs_reorder"]]
    fast_count = sum(1 for i in items if i.get("turnover_category") == "fast")
    slow_count = sum(1 for i in items if i.get("turnover_category") == "slow")
    avg_turnover = (
        round(sum(turnover_days_list) / len(turnover_days_list), 1)
        if turnover_days_list
        else 0
    )

    summary = {
        "total_skus": len(items),
        "reorder_count": len(reorder_items),
        "urgent_count": urgent_count,
        "normal_count": normal_count,
        "planned_count": planned_count,
        "total_reorder_qty": total_reorder_qty,
        "total_reorder_value": round(total_reorder_value, 2),
        "fast_moving_count": fast_count,
        "slow_moving_count": slow_count,
        "total_capital": round(total_capital, 2),
        "avg_turnover_days": avg_turnover,
        "stale_count": stale_count,
        "stockout_count": sum(1 for i in items if i["status"] == "stockout"),
        "overstock_count": sum(1 for i in items if i["status"] == "overstock"),
        "healthy_count": sum(1 for i in items if i["status"] == "healthy"),
        "periods": periods,
        "procurement_days": PROCUREMENT_DAYS,
        "weighted_months": WEIGHTED_MONTHS,
        "month_weights": MONTH_WEIGHTS,
        "safety_factor_fast": SAFETY_FACTOR_FAST,
        "safety_factor_slow": SAFETY_FACTOR_SLOW,
        "turnover_threshold_days": TURNOVER_THRESHOLD_DAYS,
        # 兼容旧字段：数据范围
        "date_span": sum(_days_in_month(p) for p in periods),
        "data_start": periods[-1] if periods else None,
        "data_end": periods[0] if periods else None,
    }

    return {
        "summary": summary,
        "items": items,
    }
