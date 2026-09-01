"""
Analysis Routes - 高级分析 API.

Endpoints:
- GET /analysis/abc         - ABC分类分析
- GET /analysis/gmroi       - GMROI库存投资回报
- GET /analysis/forecast    - 销售预测
- GET /analysis/cashflow    - 现金流预测
- GET /analysis/interval    - 最优经营区间
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.analysis_service import analysis_service

router = APIRouter()


@router.get("/analysis/abc")
def get_abc_analysis(
    period: Optional[str] = Query(None, description="期间 YYYY-MM"),
    brand: Optional[str] = Query(None, description="品牌"),
    metric: str = Query("revenue", description="分类依据: revenue / profit"),
    db: Session = Depends(get_db),
):
    """ABC分类分析 - SKU按收入/利润贡献分类."""
    return analysis_service.get_abc_analysis(db, period=period, brand=brand, metric=metric)


@router.get("/analysis/gmroi")
def get_gmroi_analysis(
    period: Optional[str] = Query(None, description="期间 YYYY-MM"),
    brand: Optional[str] = Query(None, description="品牌"),
    db: Session = Depends(get_db),
):
    """GMROI - 库存投资毛利率回报."""
    return analysis_service.get_gmroi_analysis(db, period=period, brand=brand)


@router.get("/analysis/forecast")
def get_sales_forecast(
    brand: Optional[str] = Query(None, description="品牌"),
    forecast_months: int = Query(3, description="预测月数"),
    db: Session = Depends(get_db),
):
    """销售预测 - 基于线性回归."""
    return analysis_service.get_sales_forecast(db, brand=brand, forecast_months=forecast_months)


@router.get("/analysis/cashflow")
def get_cashflow_forecast(
    brand: Optional[str] = Query(None, description="品牌"),
    forecast_months: int = Query(3, description="预测月数"),
    db: Session = Depends(get_db),
):
    """现金流预测."""
    return analysis_service.get_cashflow_forecast(db, brand=brand, forecast_months=forecast_months)


@router.get("/analysis/interval")
def get_optimal_interval(
    brand: Optional[str] = Query(None, description="品牌"),
    db: Session = Depends(get_db),
):
    """最优经营区间分析 - 不同折扣率的利润表现."""
    return analysis_service.get_optimal_interval(db, brand=brand)
