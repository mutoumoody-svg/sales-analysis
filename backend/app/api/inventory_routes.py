"""
Inventory routes - 库存分析接口.
包含：库存健康、周转分析、滞销分析、补货建议、资金占用.
Dashboard: 企业健康指数 + CEO日报.
支持按月份筛选（month 参数，格式 YYYY-MM，用于 sales_summary 数据过滤）。
补货建议使用 reorder_service 统一引擎（近6个月加权日均 + 2个月采购周期 + 动态安全系数）。
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
from app.services.reorder_service import calculate_reorder
from app.services.wangdian_sync_service import (
    sync_from_wangdian as _sync_from_wangdian,
    get_wangdian_sync_status as _get_wangdian_sync_status,
)
from app.core.config import settings

router = APIRouter()


# ===== 旺店通 API 库存同步 =====

@router.get("/inventory/wangdian-sync-status")
def wangdian_sync_status(db: Session = Depends(get_db)) -> Dict:
    """查询旺店通API库存同步状态.

    返回:
        configured: 是否已配置旺店通凭证
        within_allowed_time: 当前是否在允许调用时间段（00:00-02:00）
        last_sync_at: 上次同步时间
        last_synced_date: 上次同步的日期
        last_total_from_api: 上次从API拉取的记录总数
        last_matched: 上次匹配的SKU数
        last_inserted/updated: 上次新增/更新记录数
        last_warehouses: 上次同步覆盖的仓库列表
        sales_analysis_latest_date: inventory表最新日期
    """
    return {"status": "success", "data": _get_wangdian_sync_status(db)}


@router.post("/inventory/sync-from-wangdian")
def trigger_sync_from_wangdian(db: Session = Depends(get_db)) -> Dict:
    """触发从旺店通API同步库存到 sales-analysis.

    调用旺店通 stock_query_all.php 接口拉取全量库存数据，
    按 SKU 匹配 products 表，upsert 到 inventory 表。

    注意:
        - 正式环境只允许凌晨 00:00-02:00 调用
        - 需要在 .env 中配置 WANGDIAN_SID / WANGDIAN_APPKEY / WANGDIAN_APPSECRET
        - 幂等：同一日期重复同步不会产生重复记录
    """
    sid = settings.WANGDIAN_SID
    appkey = settings.WANGDIAN_APPKEY
    appsecret = settings.WANGDIAN_APPSECRET

    if not sid or not appkey or not appsecret:
        return {
            "status": "error",
            "message": "未配置旺店通API凭证，请在 .env 文件中设置 WANGDIAN_SID / WANGDIAN_APPKEY / WANGDIAN_APPSECRET",
        }

    result = _sync_from_wangdian(
        db=db,
        sid=sid,
        appkey=appkey,
        appsecret=appsecret,
        sandbox=settings.WANGDIAN_SANDBOX,
    )
    return result


@router.get("/inventory/health")
def inventory_health(
    warehouse: Optional[str] = Query(None, description="仓库"),
    as_of_date: Optional[date] = Query(None, description="截至日期"),
    brand: Optional[str] = Query(None, description="品牌筛选"),
    db: Session = Depends(get_db),
) -> Dict:
    """库存健康分析: 库存评分、风险SKU."""
    # 默认只取最新日期，避免历史快照叠加导致库存虚高
    if not as_of_date:
        latest_inv_date = db.query(func.max(Inventory.date)).scalar()
    else:
        latest_inv_date = as_of_date
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
        .filter(Inventory.date == latest_inv_date)
    )

    if warehouse:
        query = query.filter(Inventory.warehouse == warehouse)
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

    使用 reorder_service 统一引擎计算：
    - 近6个月加权日均销量（权重 6/5/4/3/2/1）
    - 采购周期 60 天（2个月）
    - 动态安全系数：周转<2个月→1.7，周转≥2个月→1.3
    - 补货量 = max(安全库存 + 周期需求 - 有效库存, 周期需求)
    """
    period = resolve_period(db, month)

    result = calculate_reorder(db, period, brand=brand, warehouse=warehouse)

    summary = result.get("summary", {})
    summary["period"] = period

    return {
        "status": "success",
        "data": {
            "summary": summary,
            "items": result.get("items", []),
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
