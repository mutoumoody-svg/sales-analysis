"""
Profit routes - 利润分析接口.
数据来源: orders表（含真实毛利数据） + sales_summary表（店铺x商品维度汇总利润）.
利润层级:
  毛利 = 订单金额 - 货品成本
  贡献利润 = 毛利 - 邮资成本 - 包装成本
  净利润 = 贡献利润（暂无固定费用分摊）
支持按月份筛选（month 参数，格式 YYYY-MM）。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Optional
from datetime import date

from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.store import Store
from app.models.product import Product
from app.models.sales_summary import SalesSummary
from app.services.system_cost_service import list_missing_cost_skus
from app.utils.period import resolve_period, period_to_date_range

router = APIRouter()


def _apply_period_filter(query, period: str):
    """给 sales_summary 查询添加月份过滤."""
    return query.filter(SalesSummary.period == period)


# ============================================================
# 从 sales_summary 表查询利润（已扣除退货）
# ============================================================

@router.get("/profit/summary")
def profit_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    store_id: Optional[str] = Query(None, description="店铺ID"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """利润汇总: 从 sales_summary 表查询实际利润（已扣除退货）."""
    period = resolve_period(db, month)
    query = db.query(
        func.sum(SalesSummary.ship_qty).label("ship_qty"),
        func.sum(SalesSummary.return_qty).label("return_qty"),
        func.sum(SalesSummary.net_qty).label("net_qty"),
        func.sum(SalesSummary.ship_amount).label("ship_amount"),
        func.sum(SalesSummary.return_amount).label("return_amount"),
        func.sum(SalesSummary.net_amount).label("revenue"),
        func.sum(SalesSummary.net_cost).label("net_cost"),
        func.sum(SalesSummary.commission_cost).label("commission_cost"),
        func.sum(SalesSummary.ship_profit).label("ship_profit"),
        func.sum(SalesSummary.net_profit).label("net_profit"),
    )
    query = _apply_period_filter(query, period)

    if brand:
        query = query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    if store_id:
        query = query.filter(SalesSummary.store_id == store_id)

    result = query.first()

    revenue = float(result.revenue) if result.revenue else 0
    net_cost = float(result.net_cost) if result.net_cost else 0
    commission = float(result.commission_cost) if result.commission_cost else 0
    ship_profit = float(result.ship_profit) if result.ship_profit else 0
    net_profit_val = float(result.net_profit) if result.net_profit else 0
    ship_amount = float(result.ship_amount) if result.ship_amount else 0
    return_amount = float(result.return_amount) if result.return_amount else 0

    # 订单数从orders表获取（排除退货类），按月份过滤
    p_start, p_end = period_to_date_range(period)
    order_query = db.query(
        func.count(Order.id).label("order_count"),
        func.sum(Order.shipping_fee).label("shipping_fee"),
        func.sum(Order.shipping_cost).label("shipping_cost"),
        func.sum(Order.packaging_cost).label("packaging_cost"),
        func.sum(Order.discount).label("discount"),
    ).filter(
        Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
        Order.order_date >= p_start,
        Order.order_date <= p_end,
    )

    if store_id:
        order_query = order_query.filter(Order.store_id == store_id)
    if brand:
        order_query = (
            order_query
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.brand == brand)
        )

    order_result = order_query.first()

    shipping_cost_val = float(order_result.shipping_cost) if order_result.shipping_cost else 0
    packaging_cost_val = float(order_result.packaging_cost) if order_result.packaging_cost else 0

    contribution_profit = net_profit_val - commission - shipping_cost_val - packaging_cost_val
    net_profit_final = contribution_profit

    return {
        "status": "success",
        "data": {
            "order_count": order_result.order_count or 0,
            "revenue": revenue,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "net_cost": net_cost,
            "gross_profit": net_profit_val,
            "ship_profit": ship_profit,
            "gross_margin_pct": round(net_profit_val / revenue * 100, 2) if revenue > 0 else 0,
            "commission_cost": commission,
            "shipping_fee": float(order_result.shipping_fee) if order_result.shipping_fee else 0,
            "shipping_cost": shipping_cost_val,
            "packaging_cost": packaging_cost_val,
            "discount": float(order_result.discount) if order_result.discount else 0,
            "contribution_profit": round(contribution_profit, 2),
            "net_profit": round(net_profit_final, 2),
            "net_margin_pct": round(net_profit_final / revenue * 100, 2) if revenue > 0 else 0,
            "period": period,
        },
    }


@router.get("/profit/by-store")
def profit_by_store(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    limit: int = Query(50, description="返回条数", ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict:
    """按店铺利润排名 - 基于实际销售额（扣除退货）和实际成本."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Store.id.label("store_id"),
            Store.store_name,
            Store.platform,
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_cost).label("net_cost"),
            func.sum(SalesSummary.commission_cost).label("commission_cost"),
            func.sum(SalesSummary.ship_profit).label("ship_profit"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
    )
    if brand:
        query = query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    query = query.group_by(Store.id, Store.store_name, Store.platform).order_by(desc("gross_profit"))

    results = query.limit(limit).all()

    stores = []
    for r in results:
        revenue = float(r.revenue) if r.revenue else 0
        net_cost = float(r.net_cost) if r.net_cost else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0
        commission = float(r.commission_cost) if r.commission_cost else 0
        ship_amount = float(r.ship_amount) if r.ship_amount else 0
        return_amount = float(r.return_amount) if r.return_amount else 0
        contribution = gross_profit - commission

        stores.append({
            "store_id": str(r.store_id),
            "store_name": r.store_name,
            "platform": r.platform,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "order_count": 0,
            "revenue": revenue,
            "net_cost": net_cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
            "commission_cost": commission,
            "shipping_cost": 0,
            "packaging_cost": 0,
            "contribution_profit": round(contribution, 2),
            "net_profit": round(contribution, 2),
        })

    return {
        "status": "success",
        "data": {
            "stores": stores,
            "total": len(stores),
            "period": period,
        },
    }


@router.get("/profit/by-product")
def profit_by_product(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    limit: int = Query(20, description="TOP N", ge=1, le=200),
    db: Session = Depends(get_db),
) -> Dict:
    """按商品利润排名（从sales_summary表，含发货/退货/净利）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.category,
            Store.store_name,
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.net_amount).label("net_revenue"),
            func.sum(SalesSummary.net_cost).label("net_cost"),
            func.sum(SalesSummary.ship_profit).label("ship_profit"),
            func.sum(SalesSummary.net_profit).label("net_profit"),
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
        .group_by(
            Product.id, Product.sku, Product.product_name, Product.category, Store.store_name
        )
        .order_by(desc("net_profit"))
    )

    if brand:
        query = query.filter(Product.brand == brand)

    results = query.limit(limit).all()

    products = []
    for r in results:
        revenue = float(r.net_revenue) if r.net_revenue else 0
        cost = float(r.net_cost) if r.net_cost else 0
        net_profit = float(r.net_profit) if r.net_profit else 0

        products.append({
            "product_id": str(r.product_id),
            "sku": r.sku,
            "product_name": r.product_name,
            "category": r.category,
            "store_name": r.store_name,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "net_revenue": revenue,
            "net_cost": cost,
            "ship_profit": float(r.ship_profit) if r.ship_profit else 0,
            "net_profit": net_profit,
            "net_margin_pct": round(net_profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    return {
        "status": "success",
        "data": {
            "products": products,
            "total": len(products),
            "period": period,
        },
    }


@router.get("/profit/daily-trend")
def profit_daily_trend(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    store_id: Optional[str] = Query(None, description="店铺ID"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """日利润趋势（从orders表，排除退货/换货类订单）."""
    period = resolve_period(db, month)
    p_start, p_end = period_to_date_range(period)

    query = (
        db.query(
            Order.order_date.label("date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
            func.sum(Order.gross_profit).label("gross_profit"),
            func.sum(Order.shipping_cost).label("shipping_cost"),
            func.sum(Order.packaging_cost).label("packaging_cost"),
        )
        .filter(
            Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
            Order.order_date >= (start_date or p_start),
            Order.order_date <= (end_date or p_end),
        )
        .group_by(Order.order_date)
        .order_by(Order.order_date)
    )

    if brand:
        query = (
            query
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.brand == brand)
        )

    if store_id:
        query = query.filter(Order.store_id == store_id)

    results = query.all()

    daily = []
    for r in results:
        revenue = float(r.revenue) if r.revenue else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0
        shipping_cost = float(r.shipping_cost) if r.shipping_cost else 0
        packaging_cost = float(r.packaging_cost) if r.packaging_cost else 0
        contribution = gross_profit - shipping_cost - packaging_cost

        daily.append({
            "date": str(r.date),
            "order_count": r.order_count,
            "revenue": revenue,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
            "shipping_cost": shipping_cost,
            "packaging_cost": packaging_cost,
            "contribution_profit": round(contribution, 2),
            "net_profit": round(contribution, 2),
        })

    return {
        "status": "success",
        "data": {
            "daily": daily,
            "total_days": len(daily),
            "period": period,
        },
    }


@router.get("/profit/by-sku/{sku}")
def profit_by_sku(
    sku: str,
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """单SKU利润分析（从sales_summary表，含各店铺明细）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.sku,
            Product.product_name,
            Product.category,
            Store.store_name,
            Store.platform,
            SalesSummary.ship_qty,
            SalesSummary.return_qty,
            SalesSummary.net_qty,
            SalesSummary.net_amount,
            SalesSummary.net_cost,
            SalesSummary.commission_cost,
            SalesSummary.ship_profit,
            SalesSummary.net_profit,
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(Product.sku == sku, SalesSummary.period == period)
    )

    results = query.all()

    if not results:
        return {
            "status": "error",
            "message": f"SKU {sku} not found in sales_summary for period {period}",
        }

    total_revenue = sum(float(r.net_amount) for r in results)
    total_cost = sum(float(r.net_cost) for r in results)
    total_profit = sum(float(r.net_profit) for r in results)
    total_qty = sum(r.net_qty for r in results)

    store_breakdown = []
    for r in results:
        revenue = float(r.net_amount)
        store_breakdown.append({
            "store_name": r.store_name,
            "platform": r.platform,
            "net_qty": r.net_qty,
            "net_revenue": revenue,
            "net_cost": float(r.net_cost),
            "commission_cost": float(r.commission_cost),
            "net_profit": float(r.net_profit),
            "net_margin_pct": round(float(r.net_profit) / revenue * 100, 2) if revenue > 0 else 0,
        })

    return {
        "status": "success",
        "data": {
            "sku": sku,
            "product_name": results[0].product_name,
            "category": results[0].category,
            "period": period,
            "total_qty": total_qty,
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "net_margin_pct": round(total_profit / total_revenue * 100, 2) if total_revenue > 0 else 0,
            "store_count": len(results),
            "store_breakdown": store_breakdown,
        },
    }


@router.get("/profit/low-margin")
def profit_low_margin(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    limit: int = Query(20, description="返回条数", ge=1, le=200),
    db: Session = Depends(get_db),
) -> Dict:
    """低毛利商品预警（从sales_summary表，毛利率低于10%）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.sku,
            Product.product_name,
            Product.category,
            Store.store_name,
            SalesSummary.net_qty,
            SalesSummary.net_amount,
            SalesSummary.net_cost,
            SalesSummary.net_profit,
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period, SalesSummary.net_amount > 0)
    )

    if brand:
        query = query.filter(Product.brand == brand)

    results = query.all()

    items = []
    for r in results:
        revenue = float(r.net_amount) if r.net_amount else 0
        if revenue == 0:
            continue
        net_profit = float(r.net_profit) if r.net_profit else 0
        margin = net_profit / revenue * 100
        if margin < 10:
            items.append({
                "sku": r.sku,
                "product_name": r.product_name,
                "category": r.category,
                "store_name": r.store_name,
                "net_qty": r.net_qty,
                "net_revenue": revenue,
                "net_cost": float(r.net_cost),
                "net_profit": net_profit,
                "net_margin_pct": round(margin, 2),
                "risk_level": "loss" if margin < 0 else "low_margin",
            })

    items.sort(key=lambda x: x["net_margin_pct"])
    items = items[:limit]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": len(items),
            "loss_count": sum(1 for i in items if i["risk_level"] == "loss"),
            "low_margin_count": sum(1 for i in items if i["risk_level"] == "low_margin"),
            "period": period,
        },
    }


@router.get("/profit/cost-missing")
def profit_cost_missing(
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM（默认全部）"),
    db: Session = Depends(get_db),
) -> Dict:
    """列出有销售但缺系统成本(products.unit_cost) 的 SKU，供运营补录成本."""
    period = month
    items = list_missing_cost_skus(db, period)
    return {
        "status": "success",
        "data": {
            "items": items,
            "total": len(items),
            "total_missing_amount": round(sum(i["net_amount"] for i in items), 2),
        },
    }
