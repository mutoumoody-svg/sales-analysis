"""
店铺订单日报 API 路由。
数据源：旺店通 trade_query.php 抓取的每日订单 JSON。
"""

from fastapi import APIRouter, Query
from app.services.trade_daily_service import (
    get_overview, get_trend, get_by_shop, get_top_skus, get_daily_detail,
    _get_available_dates,
)

router = APIRouter()


@router.get("/shop-daily/overview")
def shop_daily_overview(
    days: int = Query(7, ge=1, le=90),
    shop: str = Query("慕咖", description="店铺名过滤，空字符串=全部"),
):
    """店铺日报概览：最近 N 天汇总 + 今天/昨天对比 + 店铺分布."""
    return {"status": "success", "data": get_overview(days, shop)}


@router.get("/shop-daily/trend")
def shop_daily_trend(
    days: int = Query(30, ge=1, le=90),
    shop: str = Query("慕咖"),
):
    """每日趋势."""
    return {"status": "success", "data": get_trend(days, shop)}


@router.get("/shop-daily/by-shop")
def shop_daily_by_shop(
    days: int = Query(7, ge=1, le=90),
    shop: str = Query("慕咖"),
):
    """按店铺汇总."""
    return {"status": "success", "data": get_by_shop(days, shop)}


@router.get("/shop-daily/top-skus")
def shop_daily_top_skus(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
    shop: str = Query("慕咖"),
):
    """Top SKU 排行（按实付金额）."""
    return {"status": "success", "data": get_top_skus(days, shop, limit)}


@router.get("/shop-daily/daily-detail")
def shop_daily_detail(
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    shop: str = Query("慕咖"),
):
    """某日明细."""
    return {"status": "success", "data": get_daily_detail(date, shop)}


@router.get("/shop-daily/available-dates")
def shop_daily_dates(
    shop: str = Query("慕咖"),
):
    """可用日期列表."""
    return {"status": "success", "data": _get_available_dates(shop)}
