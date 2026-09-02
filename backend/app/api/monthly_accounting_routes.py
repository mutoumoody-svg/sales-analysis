"""Monthly accounting synchronization and reconciliation APIs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models.monthly_accounting import MonthlyAccountingBatch, MonthlyAccountingStore
from app.models.sales_summary import SalesSummary
from app.services.monthly_accounting_service import available_source_periods, sync_period

router = APIRouter()


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
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "success", "data": _batch_dict(batch)}


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

