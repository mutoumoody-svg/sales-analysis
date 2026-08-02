"""
Expense model - 费用表.
For calculating true profit (contribution profit and net profit).
"""

import uuid
from sqlalchemy import Column, String, Date, Numeric, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Expense(Base):
    """费用表 - expenses for profit calculation.

    expense_type values:
    - Advertising  (广告费用)
    - Platform Fee (平台费用)
    - Shipping     (物流费用)
    - Gift         (赠品成本)
    - Operation    (运营费用)
    - Fixed        (固定费用)
    """

    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True, comment="店铺")
    expense_type = Column(String(30), nullable=False, comment="费用类型")
    amount = Column(Numeric(14, 2), nullable=False, comment="金额")
    date = Column(Date, nullable=False, index=True, comment="日期")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
