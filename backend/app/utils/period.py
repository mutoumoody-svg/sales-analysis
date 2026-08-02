"""
Period helper - 月份筛选工具.
用于 sales_summary 按 period (YYYY-MM) 过滤，以及 orders 按 日期范围 过滤.
"""

from typing import Optional
from datetime import date
import calendar

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.sales_summary import SalesSummary


def get_latest_period(db: Session) -> str:
    """获取 sales_summary 中最新的 period."""
    result = db.query(func.max(SalesSummary.period)).scalar()
    return result or date.today().strftime("%Y-%m")


def get_available_periods(db: Session) -> list[dict]:
    """获取所有可用月份列表，按降序排列."""
    results = (
        db.query(
            SalesSummary.period,
            func.count(SalesSummary.id).label("row_count"),
            func.sum(SalesSummary.net_amount).label("net_revenue"),
        )
        .group_by(SalesSummary.period)
        .order_by(SalesSummary.period.desc())
        .all()
    )
    return [
        {
            "period": r.period,
            "row_count": r.row_count,
            "net_revenue": float(r.net_revenue) if r.net_revenue else 0,
        }
        for r in results
    ]


def resolve_period(db: Session, month: Optional[str]) -> str:
    """解析 period：如果传了 month 就用，否则取最新."""
    if month:
        return month
    return get_latest_period(db)


def period_to_date_range(period: str) -> tuple[date, date]:
    """将 YYYY-MM 转换为 (月初日期, 月末日期)."""
    year, month = period.split("-")
    year, month = int(year), int(month)
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end
