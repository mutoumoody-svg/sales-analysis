"""Synchronize confirmed month results produced by the legacy sales dashboard."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.monthly_accounting import MonthlyAccountingBatch, MonthlyAccountingStore


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _integer(value) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def results_file(period: str) -> Path:
    if len(period) != 7 or period[4] != "-":
        raise ValueError("period must use YYYY-MM")
    base = settings.SALES_AGENT_DATA_PATH.strip()
    if not base:
        raise FileNotFoundError("SALES_AGENT_DATA_PATH is not configured")
    return Path(base) / f"results_{period.replace('-', '')}.json"


def available_source_periods() -> list[str]:
    base = settings.SALES_AGENT_DATA_PATH.strip()
    if not base or not Path(base).is_dir():
        return []
    periods = []
    for path in Path(base).glob("results_??????.json"):
        token = path.stem.removeprefix("results_")
        if len(token) == 6 and token.isdigit():
            periods.append(f"{token[:4]}-{token[4:]}")
    return sorted(set(periods))


def sync_period(db: Session, period: str) -> MonthlyAccountingBatch:
    path = results_file(period)
    if not path.is_file():
        raise FileNotFoundError(f"monthly result not found: {period}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError("monthly result is empty or invalid")

    batch = db.query(MonthlyAccountingBatch).filter_by(period=period).first()
    if not batch:
        batch = MonthlyAccountingBatch(period=period)
        db.add(batch)
        db.flush()
    else:
        db.query(MonthlyAccountingStore).filter_by(batch_id=batch.id).delete()

    totals = {"revenue": Decimal(0), "cost": Decimal(0), "gross": Decimal(0), "operating": Decimal(0)}
    for source_key, item in payload.items():
        summary = item.get("summary") or {}
        revenue = _money(summary.get("总销售额(商家收入)"))
        cost = _money(summary.get("合计总成本"))
        gross = _money(summary.get("总毛利润"))
        operating = _money(summary.get("营销后净利润", gross))
        platform = str(item.get("platform") or "未知")
        platform_fee = _money(summary.get(f"{platform}平台费用"))
        tax_fee = _money(summary.get(f"{platform}税费", summary.get("合计税费")))
        row = MonthlyAccountingStore(
            batch_id=batch.id,
            store_name=str(item.get("name") or source_key),
            platform=platform,
            source_key=source_key,
            revenue=revenue,
            cost=cost,
            gross_profit=gross,
            ad_fee=_money(summary.get("广告费用", summary.get("推广费用合计"))),
            platform_fee=platform_fee,
            tax_fee=tax_fee,
            logistics_fee=_money(summary.get("🚚 仓储快递费")),
            operating_profit=operating,
            order_count=_integer(summary.get("总订单数")),
            sales_qty=_integer(summary.get("总销量(正品)")),
        )
        db.add(row)
        totals["revenue"] += revenue
        totals["cost"] += cost
        totals["gross"] += gross
        totals["operating"] += operating

    batch.store_count = len(payload)
    batch.revenue = totals["revenue"]
    batch.cost = totals["cost"]
    batch.gross_profit = totals["gross"]
    batch.operating_profit = totals["operating"]
    batch.status = "confirmed"
    batch.synced_at = datetime.utcnow()
    db.commit()
    db.refresh(batch)
    return batch

