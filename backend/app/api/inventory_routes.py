"""
Inventory routes - 库存分析接口.
包含：库存健康、周转分析、滞销分析、补货建议、资金占用.
Dashboard: 企业健康指数 + CEO日报.
支持按月份筛选（month 参数，格式 YYYY-MM，用于 sales_summary 数据过滤）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Dict, Optional
from datetime import date, timedelta

from app.database import get_db
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.sales_summary import SalesSummary
from app.models.order import Order, OrderItem
from app.utils.period import resolve_period, period_to_date_range, get_latest_period

router = APIRouter()

# 采购周期天数（可后续做成配置）
PROCUREMENT_DAYS = 30


@router.get("/inventory/health")
def inventory_health(
    warehouse: Optional[str] = Query(None, description="仓库"),
    as_of_date: Optional[date] = Query(None, description="截至日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """库存健康分析: 库存评分、风险SKU."""
    query = (
        db.query(
            Product.sku,
            Product.product_name,
            Product.brand,
            Inventory.warehouse,
            func.sum(Inventory.available_qty).label("available"),
            func.sum(Inventory.reserved_qty).label("reserved"),
            func.sum(Inventory.inbound_qty).label("inbound"),
        )
        .join(Product, Inventory.product_id == Product.id)
    )

    if warehouse:
        query = query.filter(Inventory.warehouse == warehouse)
    if as_of_date:
        query = query.filter(Inventory.date <= as_of_date)
    if brand:
        query = query.filter(Product.brand == brand)

    query = query.group_by(Product.sku, Product.product_name, Product.brand, Inventory.warehouse)
    results = query.all()

    items = []
    for r in results:
        available = int(r.available) if r.available else 0
        reserved = int(r.reserved) if r.reserved else 0
        inbound = int(r.inbound) if r.inbound else 0
        effective = available + inbound - reserved

        if available == 0 and inbound == 0:
            risk_level = "stockout"
        elif available > 0 and available < 10:
            risk_level = "low_stock"
        elif available > 100:
            risk_level = "overstock"
        else:
            risk_level = "healthy"

        items.append({
            "sku": r.sku,
            "product_name": r.product_name,
            "brand": r.brand,
            "warehouse": r.warehouse,
            "available_qty": available,
            "reserved_qty": reserved,
            "inbound_qty": inbound,
            "effective_qty": effective,
            "risk_level": risk_level,
        })

    total_skus = len(items)
    stockout_count = sum(1 for i in items if i["risk_level"] == "stockout")
    low_stock_count = sum(1 for i in items if i["risk_level"] == "low_stock")
    overstock_count = sum(1 for i in items if i["risk_level"] == "overstock")

    if total_skus > 0:
        healthy_count = total_skus - stockout_count - low_stock_count - overstock_count
        health_score = round(healthy_count / total_skus * 100, 1)
    else:
        health_score = 0

    return {
        "status": "success",
        "data": {
            "health_score": health_score,
            "total_skus": total_skus,
            "stockout_count": stockout_count,
            "low_stock_count": low_stock_count,
            "overstock_count": overstock_count,
            "items": items,
        },
    }


@router.get("/inventory/analysis")
def inventory_analysis(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    warehouse: Optional[str] = Query(None, description="仓库"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM（用于销售数据过滤）"),
    db: Session = Depends(get_db),
) -> Dict:
    """库存深度分析: 周转天数、滞销分析、补货建议、资金占用.
    
    month 参数用于过滤 sales_summary 的销售数据。
    库存数据始终取最新快照。
    """
    period = resolve_period(db, month)

    # 1. 获取销售数据日期范围（从 orders 表，按月份过滤）
    p_start, p_end = period_to_date_range(period)
    date_range = db.query(
        func.min(Order.order_date).label("start"),
        func.max(Order.order_date).label("end"),
    ).filter(
        Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
        Order.order_date >= p_start,
        Order.order_date <= p_end,
    ).first()

    if not date_range or not date_range.start or not date_range.end:
        # 该月份无订单数据，但库存仍然展示
        date_span = 30  # 默认30天
        today = p_end
    else:
        date_span = (date_range.end - date_range.start).days + 1
        today = date_range.end

    # 2. 获取当前库存（取最新日期的记录）
    latest_inv_date = db.query(func.max(Inventory.date)).scalar()

    inv_query = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.brand,
            Product.unit_cost,
            Inventory.warehouse,
            func.sum(Inventory.available_qty).label("available"),
            func.sum(Inventory.reserved_qty).label("reserved"),
            func.sum(Inventory.inbound_qty).label("inbound"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .filter(Inventory.date == latest_inv_date)
    )
    if brand:
        inv_query = inv_query.filter(Product.brand == brand)
    if warehouse:
        inv_query = inv_query.filter(Inventory.warehouse == warehouse)

    inv_query = inv_query.group_by(
        Product.id, Product.sku, Product.product_name, Product.brand, Product.unit_cost, Inventory.warehouse
    )
    inv_results = inv_query.all()

    # 3. 获取每个商品的总销量（从 sales_summary，按月份过滤）
    sales_query = (
        db.query(
            SalesSummary.product_id,
            func.sum(SalesSummary.net_qty).label("total_qty"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
        )
        .filter(SalesSummary.period == period)
        .group_by(SalesSummary.product_id)
    )
    sales_map = {}
    for s in sales_query.all():
        sales_map[str(s.product_id)] = {
            "qty": int(s.total_qty) if s.total_qty else 0,
            "revenue": float(s.total_revenue) if s.total_revenue else 0,
        }

    # 4. 获取每个商品最后销售日期（从 order_items join orders，按月份过滤）
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
    last_sale_map = {str(r.product_id): r.last_sale_date for r in last_sale_query.all()}

    # 5. 组装分析数据
    items = []
    total_capital = 0.0
    turnover_days_list = []
    stale_count = 0
    reorder_count = 0

    for r in inv_results:
        available = int(r.available) if r.available else 0
        reserved = int(r.reserved) if r.reserved else 0
        inbound = int(r.inbound) if r.inbound else 0
        effective = available + inbound - reserved
        unit_cost = float(r.unit_cost) if r.unit_cost else 0

        pid = str(r.product_id)
        sales_info = sales_map.get(pid, {"qty": 0, "revenue": 0})
        total_sold_qty = sales_info["qty"]

        # 日均销量
        daily_rate = total_sold_qty / date_span if date_span > 0 and total_sold_qty > 0 else 0

        # 周转天数 = 当前库存 / 日均销量
        if daily_rate > 0:
            turnover_days = round(available / daily_rate, 1)
            turnover_days_list.append(turnover_days)
        else:
            turnover_days = None

        # 最后销售日期 & 滞销天数
        last_sale = last_sale_map.get(pid)
        if last_sale:
            stale_days = (today - last_sale).days
        else:
            stale_days = None

        # 滞销判定：30天以上无销售且有库存
        is_stale = (stale_days is not None and stale_days >= 30 and available > 0) or \
                   (stale_days is None and available > 0)
        if is_stale:
            stale_count += 1

        # 安全库存 = 日均销量 × 采购周期
        safety_stock = round(daily_rate * PROCUREMENT_DAYS, 0)

        # 建议补货量 = 安全库存 × 2 - 有效库存
        reorder_qty = max(0, int(safety_stock * 2 - effective))
        needs_reorder = reorder_qty > 0 and available < safety_stock
        if needs_reorder:
            reorder_count += 1

        # 资金占用 = 可售库存 × 单位成本
        capital_occupied = available * unit_cost
        total_capital += capital_occupied

        # 综合状态
        if available == 0 and inbound == 0:
            status = "stockout"
        elif is_stale:
            status = "stale"
        elif needs_reorder:
            status = "reorder"
        elif available > safety_stock * 3 and safety_stock > 0:
            status = "overstock"
        else:
            status = "healthy"

        items.append({
            "sku": r.sku,
            "product_name": r.product_name,
            "brand": r.brand,
            "warehouse": r.warehouse,
            "available_qty": available,
            "reserved_qty": reserved,
            "inbound_qty": inbound,
            "effective_qty": effective,
            "unit_cost": unit_cost,
            "capital_occupied": round(capital_occupied, 2),
            "total_sold_qty": total_sold_qty,
            "daily_rate": round(daily_rate, 2),
            "turnover_days": turnover_days,
            "last_sale_date": last_sale.isoformat() if last_sale else None,
            "stale_days": stale_days,
            "is_stale": is_stale,
            "safety_stock": int(safety_stock),
            "reorder_qty": reorder_qty,
            "needs_reorder": needs_reorder,
            "status": status,
        })

    items.sort(key=lambda x: x["capital_occupied"], reverse=True)

    avg_turnover = round(sum(turnover_days_list) / len(turnover_days_list), 1) if turnover_days_list else 0

    summary = {
        "total_capital": round(total_capital, 2),
        "avg_turnover_days": avg_turnover,
        "stale_count": stale_count,
        "reorder_count": reorder_count,
        "total_skus": len(items),
        "stockout_count": sum(1 for i in items if i["status"] == "stockout"),
        "overstock_count": sum(1 for i in items if i["status"] == "overstock"),
        "healthy_count": sum(1 for i in items if i["status"] == "healthy"),
        "date_span": date_span,
        "data_start": date_range.start.isoformat() if date_range and date_range.start else p_start.isoformat(),
        "data_end": date_range.end.isoformat() if date_range and date_range.end else p_end.isoformat(),
        "period": period,
    }

    return {
        "status": "success",
        "data": {
            "summary": summary,
            "items": items,
        },
    }


@router.get("/dashboard/health-index")
def health_index(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """企业健康指数: 销售健康 / 库存健康 / 利润健康 / 综合评分."""
    period = resolve_period(db, month)

    # 1. 销售健康：基于退货率和订单量
    sales_query = (
        db.query(
            func.sum(SalesSummary.ship_amount).label("ship"),
            func.sum(SalesSummary.return_amount).label("returns"),
            func.sum(SalesSummary.net_amount).label("net_revenue"),
            func.sum(SalesSummary.net_profit).label("net_profit"),
            func.sum(SalesSummary.net_cost).label("net_cost"),
        )
        .filter(SalesSummary.period == period)
    )
    if brand:
        sales_query = sales_query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    sales_data = sales_query.first()

    ship_amount = float(sales_data.ship) if sales_data.ship else 0
    return_amount = float(sales_data.returns) if sales_data.returns else 0
    net_revenue = float(sales_data.net_revenue) if sales_data.net_revenue else 0
    net_profit = float(sales_data.net_profit) if sales_data.net_profit else 0
    net_cost = float(sales_data.net_cost) if sales_data.net_cost else 0

    return_rate = (return_amount / ship_amount * 100) if ship_amount > 0 else 0
    if return_rate <= 5:
        sales_health = 90 + (5 - return_rate) * 2
    elif return_rate <= 15:
        sales_health = 60 + (15 - return_rate) * 3
    else:
        sales_health = max(0, 60 - (return_rate - 15) * 2)
    sales_health = round(min(100, max(0, sales_health)), 1)

    # 2. 库存健康：基于库存风险分布
    latest_inv_date = db.query(func.max(Inventory.date)).scalar()
    inv_query = (
        db.query(
            Product.id,
            func.sum(Inventory.available_qty).label("available"),
            func.sum(Inventory.inbound_qty).label("inbound"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .filter(Inventory.date == latest_inv_date)
    )
    if brand:
        inv_query = inv_query.filter(Product.brand == brand)
    inv_query = inv_query.group_by(Product.id)
    inv_items = inv_query.all()

    total_inv_skus = len(inv_items)
    stockout = sum(1 for i in inv_items if (int(i.available) if i.available else 0) == 0 and (int(i.inbound) if i.inbound else 0) == 0)
    low_stock = sum(1 for i in inv_items if 0 < (int(i.available) if i.available else 0) < 10)
    if total_inv_skus > 0:
        healthy_inv = total_inv_skus - stockout - low_stock
        inventory_health = round(healthy_inv / total_inv_skus * 100, 1)
    else:
        inventory_health = 0

    # 3. 利润健康：基于毛利率
    gross_margin = (net_profit / net_revenue * 100) if net_revenue > 0 else 0
    if gross_margin >= 70:
        profit_health = 90 + min(10, (gross_margin - 70) * 0.5)
    elif gross_margin >= 40:
        profit_health = 60 + (gross_margin - 40) * 1.0
    elif gross_margin >= 20:
        profit_health = 30 + (gross_margin - 20) * 1.5
    else:
        profit_health = max(0, gross_margin * 1.5)
    profit_health = round(min(100, max(0, profit_health)), 1)

    # 4. 综合评分
    overall = round(profit_health * 0.4 + sales_health * 0.3 + inventory_health * 0.3, 1)

    if overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "status": "success",
        "data": {
            "overall_score": overall,
            "grade": grade,
            "sales_health": sales_health,
            "inventory_health": inventory_health,
            "profit_health": profit_health,
            "period": period,
            "metrics": {
                "net_revenue": round(net_revenue, 2),
                "net_profit": round(net_profit, 2),
                "gross_margin": round(gross_margin, 2),
                "return_rate": round(return_rate, 2),
                "total_inv_skus": total_inv_skus,
                "stockout_count": stockout,
                "low_stock_count": low_stock,
            },
        },
    }


@router.get("/dashboard/ceo-report")
def ceo_report(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """CEO日报: 最大机会 + 最大风险 + 建议动作."""
    period = resolve_period(db, month)

    # === 获取核心数据 ===
    sales_query = (
        db.query(
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_cost).label("cost"),
            func.sum(SalesSummary.net_profit).label("profit"),
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
        )
        .filter(SalesSummary.period == period)
    )
    if brand:
        sales_query = sales_query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    s = sales_query.first()

    revenue = float(s.revenue) if s.revenue else 0
    cost = float(s.cost) if s.cost else 0
    profit = float(s.profit) if s.profit else 0
    ship_qty = int(s.ship_qty) if s.ship_qty else 0
    return_qty = int(s.return_qty) if s.return_qty else 0
    ship_amount = float(s.ship_amount) if s.ship_amount else 0
    return_amount = float(s.return_amount) if s.return_amount else 0

    gross_margin = (profit / revenue * 100) if revenue > 0 else 0
    return_rate = (return_amount / ship_amount * 100) if ship_amount > 0 else 0

    # === 店铺表现 ===
    store_query = (
        db.query(
            SalesSummary.store_id,
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_profit).label("profit"),
        )
        .filter(SalesSummary.period == period)
        .group_by(SalesSummary.store_id)
    )
    if brand:
        store_query = store_query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    store_results = store_query.all()

    # === SKU表现 ===
    sku_query = (
        db.query(
            Product.sku,
            Product.product_name,
            func.sum(SalesSummary.net_qty).label("qty"),
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_profit).label("profit"),
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .filter(SalesSummary.period == period)
        .group_by(Product.sku, Product.product_name)
    )
    if brand:
        sku_query = sku_query.filter(Product.brand == brand)
    sku_results = sku_query.all()

    # === 库存风险 ===
    latest_inv_date = db.query(func.max(Inventory.date)).scalar()
    inv_query = (
        db.query(
            Product.sku,
            Product.product_name,
            func.sum(Inventory.available_qty).label("available"),
        )
        .join(Product, Inventory.product_id == Product.id)
        .filter(Inventory.date == latest_inv_date)
        .group_by(Product.sku, Product.product_name)
    )
    if brand:
        inv_query = inv_query.filter(Product.brand == brand)
    inv_results = inv_query.all()
    stockout_skus = [r for r in inv_results if (int(r.available) if r.available else 0) == 0]

    # === 生成报告 ===
    opportunities = []
    if sku_results:
        best_sku = max(sku_results, key=lambda x: float(x.profit) if x.profit else 0)
        best_profit = float(best_sku.profit) if best_sku.profit else 0
        if best_profit > 0:
            opportunities.append({
                "title": f"明星产品「{best_sku.product_name[:20]}」贡献利润最高",
                "detail": f"利润 ¥{best_profit:,.0f}，可考虑加大推广投入",
                "priority": "high",
            })

    if store_results:
        best_store = max(store_results, key=lambda x: float(x.profit) if x.profit else 0)
        best_store_profit = float(best_store.profit) if best_store.profit else 0
        if best_store_profit > 0:
            opportunities.append({
                "title": "最优店铺利润表现突出",
                "detail": f"单店利润 ¥{best_store_profit:,.0f}，可作为其他店铺标杆",
                "priority": "medium",
            })

    if gross_margin >= 50:
        opportunities.append({
            "title": f"整体毛利率 {gross_margin:.1f}% 表现健康",
            "detail": "利润空间充足，可支撑广告投放扩张",
            "priority": "medium",
        })

    risks = []
    if return_rate > 10:
        risks.append({
            "title": f"退货率 {return_rate:.1f}% 偏高",
            "detail": f"退货金额 ¥{return_amount:,.0f}，建议排查产品质量和描述一致性",
            "priority": "high",
        })
    elif return_rate > 5:
        risks.append({
            "title": f"退货率 {return_rate:.1f}% 需关注",
            "detail": "建议持续监控退货趋势，优化产品详情页",
            "priority": "medium",
        })

    if stockout_skus:
        risks.append({
            "title": f"{len(stockout_skus)} 个SKU缺货",
            "detail": f"缺货SKU包括: {', '.join([r.product_name[:15] for r in stockout_skus[:3]])}{'...' if len(stockout_skus) > 3 else ''}",
            "priority": "high",
        })

    stale_skus = []
    for inv in inv_results:
        avail = int(inv.available) if inv.available else 0
        if avail > 50:
            sku_sales = [sr for sr in sku_results if sr.sku == inv.sku]
            if not sku_sales or all((int(s.qty) if s.qty else 0) == 0 for s in sku_sales):
                stale_skus.append(inv)
    if stale_skus:
        risks.append({
            "title": f"{len(stale_skus)} 个SKU库存积压且有货不卖",
            "detail": f"积压库存资金占用，建议促销清仓: {', '.join([r.product_name[:15] for r in stale_skus[:3]])}{'...' if len(stale_skus) > 3 else ''}",
            "priority": "medium",
        })

    low_margin_skus = [r for r in sku_results if r.profit and float(r.profit) < 0]
    if low_margin_skus:
        risks.append({
            "title": f"{len(low_margin_skus)} 个SKU亏损",
            "detail": "建议优化成本或调整定价策略",
            "priority": "high",
        })

    actions = []
    if stockout_skus:
        actions.append("立即安排缺货SKU补货，避免持续损失销售机会")
    if return_rate > 10:
        actions.append("召开退货分析会议，定位高退货率根因")
    if stale_skus:
        actions.append("制定积压库存清仓计划，通过促销/捆绑销售回收资金")
    if gross_margin < 40:
        actions.append("审查产品定价和成本结构，提升整体毛利率")
    if gross_margin >= 60 and revenue > 500000:
        actions.append("毛利率健康，建议加大广告投放扩大规模")
    if not actions:
        actions.append("各项指标平稳，持续监控日常运营数据")

    opportunities = opportunities[:3]
    risks = risks[:3]
    actions = actions[:5]

    return {
        "status": "success",
        "data": {
            "summary": {
                "revenue": round(revenue, 2),
                "profit": round(profit, 2),
                "gross_margin": round(gross_margin, 2),
                "return_rate": round(return_rate, 2),
                "ship_qty": ship_qty,
                "return_qty": return_qty,
                "sku_count": len(sku_results),
                "stockout_count": len(stockout_skus),
                "period": period,
            },
            "opportunities": opportunities,
            "risks": risks,
            "actions": actions,
        },
    }
