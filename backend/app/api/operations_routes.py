"""Operational APIs: cost governance, data quality and purchase workflow."""

import calendar
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.database import get_db
from app.models.ai_recommendation import AIRecommendation
from app.models.inventory import Inventory
from app.models.monthly_accounting import MonthlyAccountingBatch
from app.models.product import Product
from app.models.purchase_plan import PurchasePlan
from app.models.sales_summary import SalesSummary
from app.models.sku_cost import SkuCost
from app.models.store import Store
from app.services.cost_service import CostMissingError, get_unit_cost
from app.services.reorder_service import calculate_reorder
from app.utils.period import resolve_period

router = APIRouter()


def _latest_json_date(directory: Path) -> date | None:
    if not directory.is_dir():
        return None
    dates = []
    for path in directory.glob("*.json"):
        try:
            dates.append(date.fromisoformat(path.stem[:10]))
        except ValueError:
            continue
    return max(dates) if dates else None


class CostUpsert(BaseModel):
    product_id: UUID
    cost_type: Literal["store", "channel", "standard", "default"]
    unit_cost: Decimal = Field(gt=0)
    effective_date: date
    store_id: UUID | None = None
    channel: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.cost_type == "store" and not self.store_id:
            raise ValueError("store cost requires store_id")
        if self.cost_type == "channel" and not self.channel:
            raise ValueError("channel cost requires channel")
        return self


class PurchaseUpdate(BaseModel):
    confirmed_qty: int = Field(ge=0)
    status: Literal["confirmed", "cancelled"] = "confirmed"
    confirmed_by: str = Field(min_length=1, max_length=100)
    notes: str | None = None
    expected_date: date | None = None


@router.get("/operations/costs")
def list_costs(
    product_id: UUID | None = None,
    store_id: UUID | None = None,
    channel: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(SkuCost, Product, Store).join(Product, SkuCost.product_id == Product.id).outerjoin(Store, SkuCost.store_id == Store.id)
    if product_id:
        q = q.filter(SkuCost.product_id == product_id)
    if store_id:
        q = q.filter(SkuCost.store_id == store_id)
    if channel:
        q = q.filter(SkuCost.channel == channel)
    rows = q.order_by(Product.sku, SkuCost.effective_date.desc()).all()
    return {"status": "success", "data": [{
        "id": str(c.id), "product_id": str(c.product_id), "sku": p.sku,
        "product_name": p.product_name, "cost_type": c.cost_type,
        "unit_cost": float(c.unit_cost), "effective_date": c.effective_date.isoformat(),
        "store_id": str(c.store_id) if c.store_id else None,
        "store_name": s.store_name if s else None, "channel": c.channel,
    } for c, p, s in rows]}


@router.post("/operations/costs", dependencies=[Depends(require_admin)])
def upsert_cost(payload: CostUpsert, db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    q = db.query(SkuCost).filter(
        SkuCost.product_id == payload.product_id,
        SkuCost.cost_type == payload.cost_type,
        SkuCost.effective_date == payload.effective_date,
    )
    if payload.store_id:
        q = q.filter(SkuCost.store_id == payload.store_id)
    else:
        q = q.filter(SkuCost.store_id.is_(None))
    if payload.channel:
        q = q.filter(SkuCost.channel == payload.channel)
    cost = q.first() or SkuCost(product_id=payload.product_id, cost_type=payload.cost_type, effective_date=payload.effective_date)
    cost.store_id = payload.store_id
    cost.channel = payload.channel.strip() if payload.channel else None
    cost.unit_cost = payload.unit_cost
    db.add(cost)
    if payload.cost_type == "standard":
        product.unit_cost = payload.unit_cost
    db.commit()
    db.refresh(cost)
    return {"status": "success", "data": {"id": str(cost.id)}}


@router.delete("/operations/costs/{cost_id}", dependencies=[Depends(require_admin)])
def delete_cost(cost_id: UUID, db: Session = Depends(get_db)):
    cost = db.get(SkuCost, cost_id)
    if not cost:
        raise HTTPException(404, "Cost record not found")
    db.delete(cost)
    db.commit()
    return {"status": "success"}


@router.post("/operations/costs/recalculate", dependencies=[Depends(require_admin)])
def recalculate_costs(month: str | None = None, db: Session = Depends(get_db)):
    period = resolve_period(db, month)
    year, month_no = map(int, period.split("-"))
    effective_on = date(year, month_no, calendar.monthrange(year, month_no)[1])
    rows = db.query(SalesSummary).filter(SalesSummary.period == period).all()
    updated = 0
    missing: list[str] = []
    for row in rows:
        try:
            unit_cost = get_unit_cost(db, str(row.product_id), str(row.store_id), effective_on)
        except CostMissingError:
            missing.append(str(row.product_id))
            row.unknown_cost_sales = row.net_amount
            continue
        row.total_cost = Decimal(row.ship_qty or 0) * unit_cost
        row.return_cost = Decimal(row.return_qty or 0) * unit_cost
        row.net_cost = Decimal(row.net_qty or 0) * unit_cost
        row.ship_profit = Decimal(row.ship_amount or 0) - row.total_cost
        row.net_profit = Decimal(row.net_amount or 0) - row.net_cost
        row.unknown_cost_sales = 0
        updated += 1
    db.commit()
    return {"status": "partial" if missing else "success", "data": {
        "period": period, "updated": updated, "missing_count": len(set(missing)),
        "missing_product_ids": sorted(set(missing)),
    }}


@router.get("/operations/data-quality")
def data_quality(month: str | None = None, db: Session = Depends(get_db)):
    period = resolve_period(db, month)
    missing_cost_query = db.query(Product.id, SalesSummary.net_amount).join(SalesSummary, SalesSummary.product_id == Product.id).outerjoin(
        SkuCost, SkuCost.product_id == Product.id,
    ).filter(
        SalesSummary.period == period,
        or_(Product.unit_cost.is_(None), Product.unit_cost <= 0),
        SkuCost.id.is_(None),
    )
    missing_rows = missing_cost_query.all()
    missing_product_ids = {str(row.id) for row in missing_rows}
    missing_cost = len(missing_product_ids)
    unknown_sales = sum(float(row.net_amount or 0) for row in missing_rows)
    unknown_brand = db.query(func.count(Product.id)).filter(or_(Product.brand.is_(None), Product.brand == "")).scalar() or 0
    unknown_category = db.query(func.count(Product.id)).filter(or_(Product.category.is_(None), Product.category == "")).scalar() or 0
    nonpositive_inventory = db.query(func.count(Inventory.id)).filter(Inventory.available_qty < 0).scalar() or 0
    return {"status": "success", "data": {
        "period": period,
        "score": round(max(0, 100
            - min(40, missing_cost * 2)
            - min(10, unknown_brand * 0.2)
            - min(15, unknown_category * 0.1)
            - min(35, nonpositive_inventory * 5)
        ), 1),
        "issues": [
            {"code": "missing_cost", "severity": "high", "count": missing_cost, "amount": float(unknown_sales)},
            {"code": "missing_brand", "severity": "medium", "count": unknown_brand},
            {"code": "missing_category", "severity": "low", "count": unknown_category},
            {"code": "negative_inventory", "severity": "high", "count": nonpositive_inventory},
        ],
    }}


@router.get("/operations/integration-status")
def integration_status(db: Session = Depends(get_db)):
    """Report whether inventory, operational sales and confirmed month close are fresh."""
    today = date.today()
    latest_inventory = db.query(func.max(Inventory.date)).scalar()
    latest_sales_period = db.query(func.max(SalesSummary.period)).scalar()
    latest_confirmed_period = db.query(func.max(MonthlyAccountingBatch.period)).filter(
        MonthlyAccountingBatch.status == "confirmed"
    ).scalar()
    realtime_date = _latest_json_date(Path("/opt/kucun/output/daily_outbound"))
    trade_date = _latest_json_date(Path("/opt/sales-analysis/output/trade_daily"))

    first_this_month = today.replace(day=1)
    previous_month_end = first_this_month.fromordinal(first_this_month.toordinal() - 1)
    expected_closed_period = previous_month_end.strftime("%Y-%m")
    checks = [
        {"key": "inventory", "label": "旺店通库存", "value": latest_inventory.isoformat() if latest_inventory else None,
         "healthy": bool(latest_inventory and (today - latest_inventory).days <= 1)},
        {"key": "realtime_sales", "label": "实时出库销售", "value": realtime_date.isoformat() if realtime_date else None,
         "healthy": bool(realtime_date and (today - realtime_date).days <= 1)},
        {"key": "shop_daily", "label": "店铺订单日报", "value": trade_date.isoformat() if trade_date else None,
         "healthy": bool(trade_date and (today - trade_date).days <= 1)},
        {"key": "operational_sales", "label": "运营销售汇总", "value": latest_sales_period,
         "healthy": bool(latest_sales_period and latest_sales_period >= expected_closed_period)},
        {"key": "monthly_accounting", "label": "确认销售月报", "value": latest_confirmed_period,
         "healthy": bool(latest_confirmed_period and latest_confirmed_period >= expected_closed_period)},
    ]
    return {"status": "success", "data": {
        "overall": "healthy" if all(item["healthy"] for item in checks) else "attention",
        "checked_at": datetime.now().isoformat(),
        "expected_closed_period": expected_closed_period,
        "checks": checks,
    }}


@router.post("/operations/purchase-plans/generate", dependencies=[Depends(require_admin)])
def generate_purchase_plans(month: str | None = None, brand: str | None = None, db: Session = Depends(get_db)):
    period = resolve_period(db, month)
    result = calculate_reorder(db, period, brand=brand)
    created = 0
    for item in result.get("items", []):
        if not item.get("needs_reorder"):
            continue
        exists = db.query(PurchasePlan).filter(PurchasePlan.product_id == item["product_id"], PurchasePlan.period == period, PurchasePlan.status == "draft").first()
        if exists:
            exists.suggested_qty = item["reorder_qty"]
            exists.unit_cost = item.get("unit_cost") or None
            exists.priority = item.get("priority", "normal")
        else:
            db.add(PurchasePlan(product_id=item["product_id"], period=period, suggested_qty=item["reorder_qty"], unit_cost=item.get("unit_cost") or None, priority=item.get("priority", "normal")))
            created += 1
    db.commit()
    return {"status": "success", "data": {"period": period, "created": created}}


@router.get("/operations/purchase-plans")
def list_purchase_plans(month: str | None = None, status: str | None = Query(None), db: Session = Depends(get_db)):
    period = resolve_period(db, month)
    q = db.query(PurchasePlan, Product).join(Product, PurchasePlan.product_id == Product.id).filter(PurchasePlan.period == period)
    if status:
        q = q.filter(PurchasePlan.status == status)
    rows = q.order_by(PurchasePlan.priority, Product.sku).all()
    return {"status": "success", "data": [{
        "id": str(plan.id), "sku": product.sku, "product_name": product.product_name,
        "suggested_qty": plan.suggested_qty, "confirmed_qty": plan.confirmed_qty,
        "unit_cost": float(plan.unit_cost) if plan.unit_cost else None,
        "status": plan.status, "priority": plan.priority, "notes": plan.notes,
        "expected_date": plan.expected_date.isoformat() if plan.expected_date else None,
    } for plan, product in rows]}


@router.patch("/operations/purchase-plans/{plan_id}", dependencies=[Depends(require_admin)])
def update_purchase_plan(plan_id: UUID, payload: PurchaseUpdate, db: Session = Depends(get_db)):
    plan = db.get(PurchasePlan, plan_id)
    if not plan:
        raise HTTPException(404, "Purchase plan not found")
    plan.confirmed_qty = payload.confirmed_qty
    plan.status = payload.status
    plan.confirmed_by = payload.confirmed_by
    plan.confirmed_at = datetime.utcnow()
    plan.notes = payload.notes
    plan.expected_date = payload.expected_date
    db.commit()
    return {"status": "success"}


@router.get("/operations/daily-alerts")
def daily_alerts(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    recs = db.query(AIRecommendation).order_by(AIRecommendation.created_at.desc()).limit(limit).all()
    return {"status": "success", "data": [{
        "id": str(r.id), "agent_type": r.agent_type, "priority": r.priority,
        "recommendation": r.recommendation, "created_at": r.created_at.isoformat(),
    } for r in recs]}
