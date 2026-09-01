"""
实时销售分析 API 路由。
数据源：kucun 系统的旺店通每日出库 JSON。
"""

from fastapi import APIRouter, Query
from app.services.realtime_sales_service import (
    get_overview, get_trend, get_top_skus,
    get_by_shop, get_by_warehouse, get_daily_detail, get_monthly_summary,
)

router = APIRouter()


@router.get("/realtime/overview")
def realtime_overview(days: int = Query(7, ge=1, le=90)):
    """实时销售概览：今天/昨天/最近N天汇总。"""
    return {"status": "success", "data": get_overview(days)}


@router.get("/realtime/trend")
def realtime_trend(days: int = Query(30, ge=1, le=90)):
    """每日销售趋势。"""
    return {"status": "success", "data": get_trend(days)}


@router.get("/realtime/top-skus")
def realtime_top_skus(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
):
    """Top SKU 排行（按销售额）。"""
    return {"status": "success", "data": get_top_skus(days, limit)}


@router.get("/realtime/by-shop")
def realtime_by_shop(days: int = Query(7, ge=1, le=90)):
    """按店铺汇总。"""
    return {"status": "success", "data": get_by_shop(days)}


@router.get("/realtime/by-warehouse")
def realtime_by_warehouse(days: int = Query(7, ge=1, le=90)):
    """按仓库汇总。"""
    return {"status": "success", "data": get_by_warehouse(days)}


@router.get("/realtime/daily-detail")
def realtime_daily_detail(date: str = Query(..., description="YYYY-MM-DD")):
    """某一天的出库明细。"""
    return {"status": "success", "data": get_daily_detail(date)}


@router.get("/realtime/monthly-summary")
def realtime_monthly_summary():
    """按月汇总（从每日数据聚合）。"""
    return {"status": "success", "data": get_monthly_summary()}
