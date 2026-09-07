"""Monthly accounting import, confirmation, reconciliation and export APIs."""

import io
import os
import tempfile
from decimal import Decimal

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models.monthly_accounting import MonthlyAccountingBatch, MonthlyAccountingStore
from app.models.sales_summary import SalesSummary
from app.services.monthly_accounting_service import (
    available_source_periods,
    save_payload,
    stage_summary_file,
    sync_operational_summary,
    sync_period,
)
from app.services.monthly_close_engine import analyze_wdt_pair

router = APIRouter()


class StoreFees(BaseModel):
    ad_fee: Decimal = Field(default=0, ge=0)
    platform_fee: Decimal = Field(default=0, ge=0)
    tax_fee: Decimal = Field(default=0, ge=0)
    logistics_fee: Decimal = Field(default=0, ge=0)


def _save_upload(upload: UploadFile) -> str:
    suffix = os.path.splitext(upload.filename or "")[1].lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(400, "Only .xlsx and .xls files are supported")
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="monthly_close_")
    os.close(fd)
    return path


def _batch_dict(batch: MonthlyAccountingBatch) -> dict:
    return {
        "id": str(batch.id), "period": batch.period, "status": batch.status,
        "source": batch.source, "store_count": batch.store_count,
        "revenue": float(batch.revenue), "cost": float(batch.cost),
        "gross_profit": float(batch.gross_profit),
        "operating_profit": float(batch.operating_profit),
        "synced_at": batch.synced_at.isoformat() if batch.synced_at else None,
    }


@router.get("/monthly-accounting/periods")
def periods(db: Session = Depends(get_db)):
    batches = db.query(MonthlyAccountingBatch).order_by(MonthlyAccountingBatch.period.desc()).all()
    return {"status": "success", "data": {
        "source_periods": available_source_periods(),
        "synced": [_batch_dict(batch) for batch in batches],
    }}


@router.post("/monthly-accounting/sync", dependencies=[Depends(require_admin)])
def sync(period: str, db: Session = Depends(get_db)):
    try:
        batch = sync_period(db, period)
        operational = sync_operational_summary(db, period)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "success", "data": _batch_dict(batch), "operational_import": operational}


@router.post("/monthly-accounting/import", dependencies=[Depends(require_admin)])
async def import_month(
    period: str = Form(...),
    detail_file: UploadFile = File(...),
    summary_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    detail_path = _save_upload(detail_file)
    summary_path = _save_upload(summary_file)
    try:
        with open(detail_path, "wb") as handle:
            handle.write(await detail_file.read())
        with open(summary_path, "wb") as handle:
            handle.write(await summary_file.read())
        payload = analyze_wdt_pair(detail_path, summary_path, period)
        batch = save_payload(db, period, payload, status="draft")
        stage_summary_file(period, summary_path)
        return {"status": "success", "data": _batch_dict(batch), "message": "双文件核算完成，请检查费用后确认月报"}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc
    finally:
        for path in (detail_path, summary_path):
            try:
                os.remove(path)
            except OSError:
                pass


@router.patch("/monthly-accounting/stores/{store_id}/fees", dependencies=[Depends(require_admin)])
def update_store_fees(store_id: str, payload: StoreFees, db: Session = Depends(get_db)):
    row = db.query(MonthlyAccountingStore).filter(MonthlyAccountingStore.id == store_id).first()
    if not row:
        raise HTTPException(404, "Monthly store result not found")
    row.ad_fee = payload.ad_fee
    row.platform_fee = payload.platform_fee
    row.tax_fee = payload.tax_fee
    row.logistics_fee = payload.logistics_fee
    row.operating_profit = row.gross_profit - payload.ad_fee - payload.platform_fee - payload.logistics_fee
    batch = db.get(MonthlyAccountingBatch, row.batch_id)
    db.flush()
    batch.operating_profit = db.query(func.coalesce(func.sum(MonthlyAccountingStore.operating_profit), 0)).filter_by(batch_id=batch.id).scalar()
    db.commit()
    return {"status": "success"}


@router.post("/monthly-accounting/confirm", dependencies=[Depends(require_admin)])
def confirm(period: str, db: Session = Depends(get_db)):
    batch = db.query(MonthlyAccountingBatch).filter_by(period=period).first()
    if not batch:
        raise HTTPException(404, "Monthly accounting period not found")
    try:
        operational = sync_operational_summary(db, period)
        batch.status = "confirmed"
        db.commit()
    except (FileNotFoundError, ValueError) as exc:
        db.rollback()
        raise HTTPException(400, f"月报尚未确认：运营销售汇总导入失败：{exc}") from exc
    return {"status": "success", "data": _batch_dict(batch), "operational_import": operational}


@router.get("/monthly-accounting/year")
def year_summary(year: int, db: Session = Depends(get_db)):
    batches = db.query(MonthlyAccountingBatch).filter(MonthlyAccountingBatch.period.like(f"{year}-%")).order_by(MonthlyAccountingBatch.period).all()
    return {"status": "success", "data": [_batch_dict(batch) for batch in batches]}


@router.get("/monthly-accounting/year-detail")
def year_detail(year: int, db: Session = Depends(get_db)):
    batches = db.query(MonthlyAccountingBatch).filter(
        MonthlyAccountingBatch.period.like(f"{year}-%")
    ).order_by(MonthlyAccountingBatch.period).all()
    batch_ids = [batch.id for batch in batches]
    stores = []
    if batch_ids:
        rows = db.query(MonthlyAccountingStore, MonthlyAccountingBatch.period).join(
            MonthlyAccountingBatch, MonthlyAccountingStore.batch_id == MonthlyAccountingBatch.id
        ).filter(MonthlyAccountingStore.batch_id.in_(batch_ids)).order_by(
            MonthlyAccountingBatch.period, MonthlyAccountingStore.revenue.desc()
        ).all()
        stores = [{
            "period": period, "store_name": row.store_name, "platform": row.platform,
            "revenue": float(row.revenue), "cost": float(row.cost),
            "gross_profit": float(row.gross_profit), "ad_fee": float(row.ad_fee),
            "platform_fee": float(row.platform_fee), "tax_fee": float(row.tax_fee),
            "logistics_fee": float(row.logistics_fee), "operating_profit": float(row.operating_profit),
            "order_count": row.order_count, "sales_qty": row.sales_qty,
        } for row, period in rows]
    return {"status": "success", "data": {
        "year": year, "months": [_batch_dict(batch) for batch in batches], "stores": stores,
    }}


@router.get("/monthly-accounting/export")
def export_month(period: str, db: Session = Depends(get_db)):
    batch = db.query(MonthlyAccountingBatch).filter_by(period=period).first()
    if not batch:
        raise HTTPException(404, "Monthly accounting period not found")
    rows = db.query(MonthlyAccountingStore).filter_by(batch_id=batch.id).order_by(MonthlyAccountingStore.revenue.desc()).all()
    frame = pd.DataFrame([{
        "月份": period, "店铺": row.store_name, "平台": row.platform,
        "销售额": float(row.revenue), "成本": float(row.cost), "毛利": float(row.gross_profit),
        "广告费": float(row.ad_fee), "平台费": float(row.platform_fee), "税费": float(row.tax_fee),
        "仓储快递费": float(row.logistics_fee), "营销后净利润": float(row.operating_profit),
        "订单数": row.order_count, "销量": row.sales_qty,
    } for row in rows])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="店铺核算")
    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="monthly-accounting-{period}.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/monthly-accounting/summary")
def summary(period: str, db: Session = Depends(get_db)):
    batch = db.query(MonthlyAccountingBatch).filter_by(period=period).first()
    if not batch:
        raise HTTPException(404, "Monthly accounting period has not been synchronized")
    stores = db.query(MonthlyAccountingStore).filter_by(batch_id=batch.id).order_by(MonthlyAccountingStore.revenue.desc()).all()
    operational = db.query(
        func.coalesce(func.sum(SalesSummary.net_amount), 0),
        func.coalesce(func.sum(SalesSummary.net_cost), 0),
        func.coalesce(func.sum(SalesSummary.net_profit), 0),
    ).filter(SalesSummary.period == period).one()
    operational_data = {"revenue": float(operational[0]), "cost": float(operational[1]), "profit": float(operational[2])}
    return {"status": "success", "data": {
        "batch": _batch_dict(batch),
        "operational": operational_data,
        "difference": {
            "revenue": float(batch.revenue) - operational_data["revenue"],
            "cost": float(batch.cost) - operational_data["cost"],
            "profit": float(batch.operating_profit) - operational_data["profit"],
        },
        "stores": [{
            "id": str(row.id), "store_name": row.store_name, "platform": row.platform,
            "revenue": float(row.revenue), "cost": float(row.cost),
            "gross_profit": float(row.gross_profit), "ad_fee": float(row.ad_fee),
            "platform_fee": float(row.platform_fee), "tax_fee": float(row.tax_fee),
            "logistics_fee": float(row.logistics_fee), "operating_profit": float(row.operating_profit),
            "order_count": row.order_count, "sales_qty": row.sales_qty,
        } for row in stores],
    }}
