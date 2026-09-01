"""
Export Routes - 数据导出 API.

Endpoints:
- GET /export/abc          - 导出ABC分析
- GET /export/gmroi        - 导出GMROI
- GET /export/forecast     - 导出销售预测
- GET /export/cashflow     - 导出现金流
- GET /export/sales        - 导出销售数据
- GET /export/profit       - 导出利润数据
- GET /export/inventory    - 导出库存数据
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.services.export_service import export_service
from app.services.analysis_service import analysis_service
from app.api import sales_routes, profit_routes, inventory_routes

router = APIRouter()


def _xlsx_response(buf, filename: str) -> Response:
    """生成Excel下载响应."""
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


def _extract_data(result) -> any:
    """从路由函数返回值中提取 data 部分."""
    if isinstance(result, dict) and "data" in result:
        return result["data"]
    return result


@router.get("/export/abc")
def export_abc(
    period: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    metric: str = Query("revenue"),
    db: Session = Depends(get_db),
):
    """导出ABC分析Excel."""
    data = analysis_service.get_abc_analysis(db, period=period, brand=brand, metric=metric)
    buf = export_service.export_abc(data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"ABC_Analysis_{ts}.xlsx")


@router.get("/export/gmroi")
def export_gmroi(
    period: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出GMROI分析Excel."""
    data = analysis_service.get_gmroi_analysis(db, period=period, brand=brand)
    buf = export_service.export_gmroi(data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"GMROI_Analysis_{ts}.xlsx")


@router.get("/export/forecast")
def export_forecast(
    brand: Optional[str] = Query(None),
    forecast_months: int = Query(3),
    db: Session = Depends(get_db),
):
    """导出销售预测Excel."""
    data = analysis_service.get_sales_forecast(db, brand=brand, forecast_months=forecast_months)
    buf = export_service.export_forecast(data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"Sales_Forecast_{ts}.xlsx")


@router.get("/export/cashflow")
def export_cashflow(
    brand: Optional[str] = Query(None),
    forecast_months: int = Query(3),
    db: Session = Depends(get_db),
):
    """导出现金流预测Excel."""
    data = analysis_service.get_cashflow_forecast(db, brand=brand, forecast_months=forecast_months)
    buf = export_service.export_cashflow(data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"Cashflow_Forecast_{ts}.xlsx")


@router.get("/export/sales")
def export_sales(
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    brand: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出销售分析Excel."""
    overview = _extract_data(sales_routes.sales_overview(brand=brand, month=month, db=db))
    by_store_result = _extract_data(sales_routes.sales_by_store(start_date=None, end_date=None, brand=brand, month=month, limit=500, db=db))
    by_store = by_store_result.get("stores", []) if isinstance(by_store_result, dict) else []
    by_product_result = _extract_data(sales_routes.sales_by_product(start_date=None, end_date=None, store_id=None, brand=brand, month=month, limit=200, db=db))
    by_product = by_product_result.get("products", []) if isinstance(by_product_result, dict) else []
    daily_result = _extract_data(sales_routes.sales_daily_trend(start_date=None, end_date=None, store_id=None, brand=brand, month=month, db=db))
    daily_trend = daily_result.get("daily", []) if isinstance(daily_result, dict) else []

    buf = export_service.export_sales_data(
        overview if isinstance(overview, dict) else {},
        by_store,
        by_product,
        daily_trend,
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"Sales_Analysis_{ts}.xlsx")


@router.get("/export/profit")
def export_profit(
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    brand: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出利润分析Excel."""
    summary = _extract_data(profit_routes.profit_summary(start_date=None, end_date=None, store_id=None, brand=brand, month=month, db=db))
    by_store_result = _extract_data(profit_routes.profit_by_store(start_date=None, end_date=None, brand=brand, month=month, limit=500, db=db))
    by_store = by_store_result.get("stores", []) if isinstance(by_store_result, dict) else []
    by_product_result = _extract_data(profit_routes.profit_by_product(brand=brand, month=month, limit=200, db=db))
    by_product = by_product_result.get("products", []) if isinstance(by_product_result, dict) else []

    buf = export_service.export_profit_data(
        summary if isinstance(summary, dict) else {},
        by_store,
        by_product,
    )
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"Profit_Analysis_{ts}.xlsx")


@router.get("/export/inventory")
def export_inventory(
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    brand: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出库存分析Excel."""
    data = _extract_data(inventory_routes.inventory_analysis(brand=brand, warehouse=None, month=month, db=db))
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    items = data.get("items", []) if isinstance(data, dict) else []

    buf = export_service.export_inventory_data(summary, items)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _xlsx_response(buf, f"Inventory_Analysis_{ts}.xlsx")
