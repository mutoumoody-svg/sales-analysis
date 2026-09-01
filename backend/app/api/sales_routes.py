"""
Sales routes - 销售分析接口.
数据来源: sales_summary 表（旺店通货品销售汇总表导入）
所有数据已扣除退货，按实际发货数量计算销售额和成本。
支持按品牌筛选（慕咖STTOKE / 慕咖（MOODY） / MoodyCoffee / 巴恩天然 / 其他）。
支持按月份筛选（month 参数，格式 YYYY-MM）。

关键字段说明:
- ship_qty / ship_amount: 发货数量 / 发货金额
- return_qty / return_amount: 退货数量 / 退货金额
- net_qty / net_amount: 实际销售量 / 实际销售额（= 发货 - 退货）
- net_cost: 实际总成本（按实际发货数量对应）
- net_profit: 实际总利润（= net_amount - net_cost - 佣金等）
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Dict, Optional
from datetime import date

from app.database import get_db
from app.models.order import Order, OrderItem
from app.models.store import Store
from app.models.product import Product
from app.models.sales_summary import SalesSummary
from app.utils.period import resolve_period, get_available_periods, period_to_date_range

router = APIRouter()


# ============================================================
# 月份列表（供前端月份选择器）
# ============================================================

@router.get("/sales/periods")
def sales_periods(db: Session = Depends(get_db)) -> Dict:
    """获取可用月份列表."""
    return {
        "status": "success",
        "data": get_available_periods(db),
    }


# ============================================================
# 基础数据列表（供前端下拉/筛选）
# ============================================================

@router.get("/brands")
def list_brands(
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """品牌列表（含销售统计）."""
    period = resolve_period(db, month)
    results = (
        db.query(
            Product.brand,
            func.count(func.distinct(Product.id)).label("product_count"),
            func.count(func.distinct(SalesSummary.store_id)).label("store_count"),
            func.sum(SalesSummary.net_amount).label("net_revenue"),
        )
        .outerjoin(SalesSummary, (SalesSummary.product_id == Product.id) & (SalesSummary.period == period))
        .filter(Product.brand.isnot(None))
        .group_by(Product.brand)
        .order_by(desc("net_revenue"))
        .all()
    )
    return {
        "status": "success",
        "data": [
            {
                "brand": r.brand,
                "product_count": r.product_count,
                "store_count": r.store_count or 0,
                "net_revenue": float(r.net_revenue) if r.net_revenue else 0,
            }
            for r in results
        ],
    }


@router.get("/stores")
def list_stores(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """店铺列表."""
    query = db.query(Store).order_by(Store.store_name)
    results = query.all()
    return {
        "status": "success",
        "data": [
            {
                "id": str(s.id),
                "store_name": s.store_name,
                "platform": s.platform,
                "channel": s.channel,
            }
            for s in results
        ],
    }


@router.get("/products")
def list_products(
    category: Optional[str] = Query(None, description="分类筛选"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> Dict:
    """商品列表."""
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if brand:
        query = query.filter(Product.brand == brand)
    results = query.order_by(Product.product_name).limit(limit).all()
    return {
        "status": "success",
        "data": [
            {
                "id": str(p.id),
                "sku": p.sku,
                "product_name": p.product_name,
                "category": p.category,
                "brand": p.brand,
            }
            for p in results
        ],
    }


@router.get("/products/categories")
def product_categories(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """商品分类列表."""
    query = (
        db.query(Product.category, func.count(Product.id).label("count"))
        .filter(Product.category.isnot(None))
    )
    if brand:
        query = query.filter(Product.brand == brand)
    results = query.group_by(Product.category).order_by(desc("count")).all()
    return {
        "status": "success",
        "data": [
            {"category": r.category, "product_count": r.count}
            for r in results
        ],
    }


# ============================================================
# 销售分析 - 全部基于 sales_summary 表（已扣除退货）
# 支持 brand + month 参数过滤
# ============================================================

def _apply_brand_filter(query, brand: Optional[str]):
    """给 sales_summary 查询添加品牌过滤（JOIN products）."""
    if brand:
        return query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    return query


def _apply_period_filter(query, period: str):
    """给 sales_summary 查询添加月份过滤."""
    return query.filter(SalesSummary.period == period)


@router.get("/sales/overview")
def sales_overview(
    brand: Optional[str] = Query(None, description="品牌筛选: 慕咖STTOKE / 慕咖（MOODY） / MoodyCoffee / 巴恩天然 / 其他"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM，不传则取最新"),
    db: Session = Depends(get_db),
) -> Dict:
    """看板首页概览: 实际销售额（扣除退货）、退货金额、实际成本、实际利润、店铺数、商品数."""
    period = resolve_period(db, month)

    # 从 sales_summary 汇总，所有金额已扣退货
    summary_query = db.query(
        func.sum(SalesSummary.ship_qty).label("total_ship_qty"),
        func.sum(SalesSummary.return_qty).label("total_return_qty"),
        func.sum(SalesSummary.net_qty).label("total_net_qty"),
        func.sum(SalesSummary.ship_amount).label("total_ship_amount"),
        func.sum(SalesSummary.return_amount).label("total_return_amount"),
        func.sum(SalesSummary.net_amount).label("total_net_revenue"),
        func.sum(SalesSummary.net_cost).label("total_net_cost"),
        func.sum(SalesSummary.commission_cost).label("total_commission"),
        func.sum(SalesSummary.net_profit).label("total_net_profit"),
        func.sum(SalesSummary.ship_profit).label("total_ship_profit"),
    )
    summary_query = _apply_period_filter(summary_query, period)
    summary_query = _apply_brand_filter(summary_query, brand)
    summary = summary_query.first()

    # 店铺数和商品数（按品牌过滤，但店铺数基于当月有销售的）
    store_count_q = (
        db.query(func.count(func.distinct(SalesSummary.store_id)))
        .filter(SalesSummary.period == period)
    )
    if brand:
        store_count_q = store_count_q.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    store_count = store_count_q.scalar() or 0

    if brand:
        product_count = db.query(func.count(Product.id)).filter(Product.brand == brand).scalar() or 0
    else:
        product_count = db.query(func.count(Product.id)).scalar() or 0

    # 从 orders 表获取日期范围和订单数（排除退货类订单），按月份过滤
    start_d, end_d = period_to_date_range(period)
    order_query = db.query(
        func.min(Order.order_date).label("min_date"),
        func.max(Order.order_date).label("max_date"),
        func.count(Order.id).label("order_count"),
        func.sum(Order.discount).label("total_discount"),
    ).filter(
        Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
        Order.order_date >= start_d,
        Order.order_date <= end_d,
    )

    if brand:
        order_query = (
            order_query
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.brand == brand)
        )

    order_stats = order_query.first()

    net_revenue = float(summary.total_net_revenue) if summary.total_net_revenue else 0
    net_cost = float(summary.total_net_cost) if summary.total_net_cost else 0
    net_profit = float(summary.total_net_profit) if summary.total_net_profit else 0
    return_amount = float(summary.total_return_amount) if summary.total_return_amount else 0
    ship_amount = float(summary.total_ship_amount) if summary.total_ship_amount else 0

    return {
        "status": "success",
        "data": {
            "brand": brand or "全部",
            "period": period,
            "total_revenue": net_revenue,
            "total_ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "order_count": order_stats.order_count or 0,
            "gross_profit": net_profit,
            "gross_margin_pct": round(net_profit / net_revenue * 100, 2) if net_revenue > 0 else 0,
            "total_cost": net_cost,
            "commission_cost": float(summary.total_commission) if summary.total_commission else 0,
            "total_discount": float(order_stats.total_discount) if order_stats.total_discount else 0,
            "store_count": store_count,
            "product_count": product_count,
            "date_range": {
                "start": str(order_stats.min_date) if order_stats.min_date else None,
                "end": str(order_stats.max_date) if order_stats.max_date else None,
            },
        },
    }


@router.get("/sales/summary")
def sales_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    store_id: Optional[str] = Query(None, description="店铺ID"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """销售汇总: 实际销售额、退货金额、实际成本、实际利润."""
    period = resolve_period(db, month)
    query = db.query(
        func.sum(SalesSummary.ship_qty).label("ship_qty"),
        func.sum(SalesSummary.return_qty).label("return_qty"),
        func.sum(SalesSummary.net_qty).label("net_qty"),
        func.sum(SalesSummary.ship_amount).label("ship_amount"),
        func.sum(SalesSummary.return_amount).label("return_amount"),
        func.sum(SalesSummary.net_amount).label("net_revenue"),
        func.sum(SalesSummary.net_cost).label("net_cost"),
        func.sum(SalesSummary.net_profit).label("net_profit"),
        func.sum(SalesSummary.commission_cost).label("commission_cost"),
    )
    query = _apply_period_filter(query, period)
    query = _apply_brand_filter(query, brand)

    if store_id:
        query = query.filter(SalesSummary.store_id == store_id)

    result = query.first()

    net_revenue = float(result.net_revenue) if result.net_revenue else 0
    net_cost = float(result.net_cost) if result.net_cost else 0
    net_profit = float(result.net_profit) if result.net_profit else 0
    ship_amount = float(result.ship_amount) if result.ship_amount else 0
    return_amount = float(result.return_amount) if result.return_amount else 0

    return {
        "status": "success",
        "data": {
            "ship_qty": int(result.ship_qty) if result.ship_qty else 0,
            "return_qty": int(result.return_qty) if result.return_qty else 0,
            "net_qty": int(result.net_qty) if result.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "net_revenue": net_revenue,
            "net_cost": net_cost,
            "net_profit": net_profit,
            "gross_margin_pct": round(net_profit / net_revenue * 100, 2) if net_revenue > 0 else 0,
            "commission_cost": float(result.commission_cost) if result.commission_cost else 0,
            "period": period,
        },
    }


@router.get("/sales/by-store")
def sales_by_store(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    limit: int = Query(50, description="返回条数", ge=1, le=500),
    db: Session = Depends(get_db),
) -> Dict:
    """按店铺销售排名 - 基于实际销售额（扣除退货）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Store.id.label("store_id"),
            Store.store_name,
            Store.platform,
            Store.channel,
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
            func.sum(SalesSummary.net_cost).label("total_cost"),
            func.sum(SalesSummary.commission_cost).label("commission_cost"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
    )
    query = _apply_brand_filter(query, brand)
    query = query.group_by(Store.id, Store.store_name, Store.platform, Store.channel).order_by(desc("total_revenue"))

    results = query.limit(limit).all()

    stores = []
    for r in results:
        revenue = float(r.total_revenue) if r.total_revenue else 0
        cost = float(r.total_cost) if r.total_cost else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0
        ship_amount = float(r.ship_amount) if r.ship_amount else 0
        return_amount = float(r.return_amount) if r.return_amount else 0

        stores.append({
            "store_id": str(r.store_id),
            "store_name": r.store_name,
            "platform": r.platform,
            "channel": r.channel,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "total_revenue": revenue,
            "total_cost": cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
            "commission_cost": float(r.commission_cost) if r.commission_cost else 0,
        })

    return {
        "status": "success",
        "data": {
            "stores": stores,
            "total": len(stores),
            "period": period,
        },
    }


@router.get("/sales/by-product")
def sales_by_product(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    store_id: Optional[str] = Query(None, description="店铺ID"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    limit: int = Query(20, description="TOP N", ge=1, le=200),
    db: Session = Depends(get_db),
) -> Dict:
    """商品销售TOP N - 基于实际销售额（扣除退货）和实际成本."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.category,
            Product.brand,
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("total_qty"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
            func.sum(SalesSummary.net_cost).label("total_cost"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .filter(SalesSummary.period == period)
        .group_by(Product.id, Product.sku, Product.product_name, Product.category, Product.brand)
        .order_by(desc("total_revenue"))
    )

    if store_id:
        query = query.filter(SalesSummary.store_id == store_id)
    if brand:
        query = query.filter(Product.brand == brand)

    results = query.limit(limit).all()

    products = []
    for r in results:
        revenue = float(r.total_revenue) if r.total_revenue else 0
        cost = float(r.total_cost) if r.total_cost else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0

        products.append({
            "product_id": str(r.product_id),
            "sku": r.sku,
            "product_name": r.product_name,
            "category": r.category,
            "brand": r.brand,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "total_qty": int(r.total_qty) if r.total_qty else 0,
            "total_revenue": revenue,
            "total_cost": cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    return {
        "status": "success",
        "data": {
            "products": products,
            "total": len(products),
            "period": period,
        },
    }


@router.get("/sales/daily-trend")
def sales_daily_trend(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    store_id: Optional[str] = Query(None, description="店铺ID"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """日销售趋势 - 从 orders 表查询，排除退货/换货类订单."""
    period = resolve_period(db, month)
    p_start, p_end = period_to_date_range(period)

    query = (
        db.query(
            Order.order_date.label("date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
            func.sum(Order.gross_profit).label("gross_profit"),
            func.sum(Order.discount).label("discount"),
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
        daily.append({
            "date": str(r.date),
            "order_count": r.order_count,
            "revenue": revenue,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
            "discount": float(r.discount) if r.discount else 0,
        })

    return {
        "status": "success",
        "data": {
            "daily": daily,
            "total_days": len(daily),
            "period": period,
        },
    }


@router.get("/sales/by-platform")
def sales_by_platform(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """按平台汇总销售 - 基于实际销售额（扣除退货）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Store.platform,
            func.count(func.distinct(Store.id)).label("store_count"),
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
            func.sum(SalesSummary.net_cost).label("total_cost"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
    )
    query = _apply_brand_filter(query, brand)
    query = query.group_by(Store.platform).order_by(desc("total_revenue"))

    results = query.all()

    platforms = []
    for r in results:
        revenue = float(r.total_revenue) if r.total_revenue else 0
        cost = float(r.total_cost) if r.total_cost else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0
        ship_amount = float(r.ship_amount) if r.ship_amount else 0
        return_amount = float(r.return_amount) if r.return_amount else 0

        platforms.append({
            "platform": r.platform,
            "store_count": r.store_count,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "total_revenue": revenue,
            "total_cost": cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    return {
        "status": "success",
        "data": {
            "platforms": platforms,
            "total": len(platforms),
            "period": period,
        },
    }


@router.get("/sales/by-category")
def sales_by_category(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """按商品分类汇总销售 - 基于实际销售额（扣除退货）."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.category,
            func.count(func.distinct(Product.id)).label("sku_count"),
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("total_qty"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
            func.sum(SalesSummary.net_cost).label("total_cost"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .filter(SalesSummary.period == period, Product.category.isnot(None))
    )
    if brand:
        query = query.filter(Product.brand == brand)
    query = query.group_by(Product.category).order_by(desc("total_revenue"))

    results = query.all()

    categories = []
    for r in results:
        revenue = float(r.total_revenue) if r.total_revenue else 0
        cost = float(r.total_cost) if r.total_cost else 0
        gross_profit = float(r.gross_profit) if r.gross_profit else 0

        categories.append({
            "category": r.category,
            "sku_count": r.sku_count,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "total_qty": int(r.total_qty) if r.total_qty else 0,
            "total_revenue": revenue,
            "total_cost": cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    return {
        "status": "success",
        "data": {
            "categories": categories,
            "total": len(categories),
            "period": period,
        },
    }


# ============================================================
# 店铺渠道分析 - 店铺商品明细 / 店铺月度趋势 / 渠道汇总
# ============================================================

@router.get("/sales/store-products")
def sales_store_products(
    store_id: str = Query(..., description="店铺ID（必传）"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM，不传则取最新"),
    limit: int = Query(200, description="返回条数", ge=1, le=1000),
    db: Session = Depends(get_db),
) -> Dict:
    """店铺内商品明细 - 指定店铺下每个SKU的销量/收入/成本/利润."""
    period = resolve_period(db, month)
    query = (
        db.query(
            Product.id.label("product_id"),
            Product.sku,
            Product.product_name,
            Product.category,
            Product.brand,
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
            func.sum(SalesSummary.net_amount).label("net_revenue"),
            func.sum(SalesSummary.net_cost).label("net_cost"),
            func.sum(SalesSummary.commission_cost).label("commission_cost"),
            func.sum(SalesSummary.net_profit).label("net_profit"),
        )
        .join(Product, SalesSummary.product_id == Product.id)
        .filter(
            SalesSummary.store_id == store_id,
            SalesSummary.period == period,
        )
        .group_by(
            Product.id, Product.sku, Product.product_name, Product.category, Product.brand
        )
        .order_by(desc("net_revenue"))
    )
    if brand:
        query = query.filter(Product.brand == brand)

    results = query.limit(limit).all()

    products = []
    for r in results:
        revenue = float(r.net_revenue) if r.net_revenue else 0
        cost = float(r.net_cost) if r.net_cost else 0
        profit = float(r.net_profit) if r.net_profit else 0
        ship_amount = float(r.ship_amount) if r.ship_amount else 0
        return_amount = float(r.return_amount) if r.return_amount else 0

        products.append({
            "product_id": str(r.product_id),
            "sku": r.sku,
            "product_name": r.product_name,
            "category": r.category,
            "brand": r.brand,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "net_revenue": revenue,
            "net_cost": cost,
            "commission_cost": float(r.commission_cost) if r.commission_cost else 0,
            "net_profit": profit,
            "gross_margin_pct": round(profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    # 汇总行
    total_revenue = sum(p["net_revenue"] for p in products)
    total_cost = sum(p["net_cost"] for p in products)
    total_profit = sum(p["net_profit"] for p in products)

    return {
        "status": "success",
        "data": {
            "products": products,
            "total": len(products),
            "period": period,
            "store_id": store_id,
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_cost": round(total_cost, 2),
                "total_profit": round(total_profit, 2),
                "gross_margin_pct": round(total_profit / total_revenue * 100, 2) if total_revenue > 0 else 0,
                "sku_count": len(products),
            },
        },
    }


@router.get("/sales/store-monthly")
def sales_store_monthly(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """各店铺逐月趋势 - 跨月对比各店铺销售额和利润."""
    query = (
        db.query(
            Store.id.label("store_id"),
            Store.store_name,
            Store.platform,
            Store.channel,
            SalesSummary.period,
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_cost).label("cost"),
            func.sum(SalesSummary.net_profit).label("profit"),
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .group_by(
            Store.id, Store.store_name, Store.platform, Store.channel, SalesSummary.period
        )
        .order_by(SalesSummary.period, desc("revenue"))
    )
    if brand:
        query = query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)

    results = query.all()

    # 收集所有月份
    all_periods = sorted(set(r.period for r in results))

    # 按 store_id 分组
    store_map: Dict[str, dict] = {}
    for r in results:
        sid = str(r.store_id)
        if sid not in store_map:
            store_map[sid] = {
                "store_id": sid,
                "store_name": r.store_name,
                "platform": r.platform,
                "channel": r.channel,
                "months": {},
            }
        store_map[sid]["months"][r.period] = {
            "revenue": float(r.revenue) if r.revenue else 0,
            "cost": float(r.cost) if r.cost else 0,
            "profit": float(r.profit) if r.profit else 0,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
        }

    # 计算每个店铺的总销售额用于排序
    stores = []
    for s in store_map.values():
        total_rev = sum(m["revenue"] for m in s["months"].values())
        total_profit = sum(m["profit"] for m in s["months"].values())
        stores.append({
            **s,
            "total_revenue": round(total_rev, 2),
            "total_profit": round(total_profit, 2),
        })
    stores.sort(key=lambda x: x["total_revenue"], reverse=True)

    return {
        "status": "success",
        "data": {
            "stores": stores,
            "periods": all_periods,
            "total_stores": len(stores),
        },
    }


@router.get("/sales/by-channel")
def sales_by_channel(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份筛选 YYYY-MM，不传则取最新"),
    db: Session = Depends(get_db),
) -> Dict:
    """按渠道汇总销售 - 渠道维度 + 平台×渠道交叉."""
    period = resolve_period(db, month)

    # 按渠道汇总
    channel_query = (
        db.query(
            func.coalesce(Store.channel, "未分类").label("channel"),
            func.count(func.distinct(Store.id)).label("store_count"),
            func.sum(SalesSummary.ship_qty).label("ship_qty"),
            func.sum(SalesSummary.return_qty).label("return_qty"),
            func.sum(SalesSummary.net_qty).label("net_qty"),
            func.sum(SalesSummary.ship_amount).label("ship_amount"),
            func.sum(SalesSummary.return_amount).label("return_amount"),
            func.sum(SalesSummary.net_amount).label("total_revenue"),
            func.sum(SalesSummary.net_cost).label("total_cost"),
            func.sum(SalesSummary.commission_cost).label("commission_cost"),
            func.sum(SalesSummary.net_profit).label("gross_profit"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
    )
    channel_query = _apply_brand_filter(channel_query, brand)
    channel_query = channel_query.group_by(func.coalesce(Store.channel, "未分类")).order_by(desc("total_revenue"))

    channel_results = channel_query.all()

    channels = []
    for r in channel_results:
        revenue = float(r.total_revenue) if r.total_revenue else 0
        cost = float(r.total_cost) if r.total_cost else 0
        profit = float(r.gross_profit) if r.gross_profit else 0
        ship_amount = float(r.ship_amount) if r.ship_amount else 0
        return_amount = float(r.return_amount) if r.return_amount else 0

        channels.append({
            "channel": r.channel,
            "store_count": r.store_count,
            "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
            "return_qty": int(r.return_qty) if r.return_qty else 0,
            "net_qty": int(r.net_qty) if r.net_qty else 0,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0,
            "total_revenue": revenue,
            "total_cost": cost,
            "commission_cost": float(r.commission_cost) if r.commission_cost else 0,
            "gross_profit": profit,
            "gross_margin_pct": round(profit / revenue * 100, 2) if revenue > 0 else 0,
        })

    # 平台×渠道交叉
    cross_query = (
        db.query(
            Store.platform,
            func.coalesce(Store.channel, "未分类").label("channel"),
            func.sum(SalesSummary.net_amount).label("revenue"),
            func.sum(SalesSummary.net_profit).label("profit"),
            func.count(func.distinct(Store.id)).label("store_count"),
        )
        .join(Store, SalesSummary.store_id == Store.id)
        .filter(SalesSummary.period == period)
    )
    cross_query = _apply_brand_filter(cross_query, brand)
    cross_query = cross_query.group_by(Store.platform, func.coalesce(Store.channel, "未分类"))

    cross_results = cross_query.all()

    cross = []
    for r in cross_results:
        cross.append({
            "platform": r.platform,
            "channel": r.channel,
            "revenue": float(r.revenue) if r.revenue else 0,
            "profit": float(r.profit) if r.profit else 0,
            "store_count": r.store_count,
        })

    return {
        "status": "success",
        "data": {
            "channels": channels,
            "cross": cross,
            "total": len(channels),
            "period": period,
        },
    }


@router.get("/sales/monthly-compare")
def sales_monthly_compare(
    months: str = Query(..., description="逗号分隔的月份列表，如 2026-04,2026-05,2026-06,2026-07"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """多月销售对比 - 按月份汇总，支持环比计算.

    返回每月: 销售额、成本、毛利、毛利率、订单数、退货率、销量、佣金等.
    """
    # 解析月份
    period_list = [m.strip() for m in months.split(",") if m.strip()]
    if not period_list:
        return {
            "status": "error",
            "message": "months 参数不能为空",
            "data": {"months": [], "comparison": []},
        }
    # 按月份升序
    period_list = sorted(set(period_list))

    # 查询每个月汇总
    query = db.query(
        SalesSummary.period,
        func.sum(SalesSummary.ship_qty).label("ship_qty"),
        func.sum(SalesSummary.return_qty).label("return_qty"),
        func.sum(SalesSummary.net_qty).label("net_qty"),
        func.sum(SalesSummary.ship_amount).label("ship_amount"),
        func.sum(SalesSummary.return_amount).label("return_amount"),
        func.sum(SalesSummary.net_amount).label("revenue"),
        func.sum(SalesSummary.net_cost).label("cost"),
        func.sum(SalesSummary.commission_cost).label("commission_cost"),
        func.sum(SalesSummary.net_profit).label("profit"),
    ).filter(SalesSummary.period.in_(period_list))

    if brand:
        query = query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
    query = query.group_by(SalesSummary.period).order_by(SalesSummary.period)

    monthly_rows = {row.period: row for row in query.all()}

    # 订单数从 orders 表按月统计
    p_start, p_end = period_to_date_range(period_list[0])  # 简单用第一个月
    p_last_start, p_last_end = period_to_date_range(period_list[-1])
    order_count_q = db.query(
        func.date_trunc("month", Order.order_date).label("month_start"),
        func.count(Order.id).label("order_count"),
    ).filter(
        Order.sales_type.in_(["Retail", "Wholesale", "Promotion", "Clearance"]),
        Order.order_date >= p_start,
        Order.order_date <= p_last_end,
    )
    if brand:
        order_count_q = (
            order_count_q
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(Product.brand == brand)
        )
    order_count_q = order_count_q.group_by(func.date_trunc("month", Order.order_date)).all()
    order_count_map: Dict[str, int] = {}
    for oc in order_count_q:
        if oc.month_start:
            key = oc.month_start.strftime("%Y-%m")
            order_count_map[key] = oc.order_count

    # 组装对比数据
    comparison = []
    prev = None
    for p in period_list:
        row = monthly_rows.get(p)
        if not row:
            continue
        revenue = float(row.revenue) if row.revenue else 0
        cost = float(row.cost) if row.cost else 0
        profit = float(row.profit) if row.profit else 0
        ship_amount = float(row.ship_amount) if row.ship_amount else 0
        return_amount = float(row.return_amount) if row.return_amount else 0
        commission = float(row.commission_cost) if row.commission_cost else 0
        net_qty = int(row.net_qty) if row.net_qty else 0
        ship_qty = int(row.ship_qty) if row.ship_qty else 0
        return_qty = int(row.return_qty) if row.return_qty else 0

        gross_margin = round(profit / revenue * 100, 2) if revenue > 0 else 0
        return_rate = round(return_amount / ship_amount * 100, 2) if ship_amount > 0 else 0

        # 环比
        revenue_mom = None
        profit_mom = None
        order_count_mom = None
        if prev:
            if prev["revenue"] > 0:
                revenue_mom = round((revenue - prev["revenue"]) / prev["revenue"] * 100, 2)
            else:
                revenue_mom = None
            if prev["profit"] != 0:
                profit_mom = round((profit - prev["profit"]) / abs(prev["profit"]) * 100, 2)
            else:
                profit_mom = None
            if prev["order_count"] > 0:
                order_count_mom = round((order_count_map.get(p, 0) - prev["order_count"]) / prev["order_count"] * 100, 2)
            else:
                order_count_mom = None

        item = {
            "month": p,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "gross_margin_pct": gross_margin,
            "ship_amount": ship_amount,
            "return_amount": return_amount,
            "return_rate": return_rate,
            "ship_qty": ship_qty,
            "return_qty": return_qty,
            "net_qty": net_qty,
            "commission_cost": commission,
            "order_count": order_count_map.get(p, 0),
            "revenue_mom": revenue_mom,
            "profit_mom": profit_mom,
            "order_count_mom": order_count_mom,
        }
        comparison.append(item)
        prev = item

    return {
        "status": "success",
        "data": {
            "months": period_list,
            "comparison": comparison,
            "total_months": len(comparison),
            "brand": brand or "全部",
        },
    }
