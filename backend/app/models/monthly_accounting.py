"""Confirmed monthly accounting results synchronized from the sales dashboard."""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class MonthlyAccountingBatch(Base):
    __tablename__ = "monthly_accounting_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period = Column(String(7), nullable=False, unique=True, index=True)
    source = Column(String(50), nullable=False, default="sales_agent")
    status = Column(String(20), nullable=False, default="confirmed")
    store_count = Column(Integer, nullable=False, default=0)
    revenue = Column(Numeric(16, 2), nullable=False, default=0)
    cost = Column(Numeric(16, 2), nullable=False, default=0)
    gross_profit = Column(Numeric(16, 2), nullable=False, default=0)
    operating_profit = Column(Numeric(16, 2), nullable=False, default=0)
    synced_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class MonthlyAccountingStore(Base):
    __tablename__ = "monthly_accounting_stores"
    __table_args__ = (
        UniqueConstraint("batch_id", "store_name", "platform", name="uq_monthly_accounting_store"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("monthly_accounting_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    store_name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)
    source_key = Column(String(250), nullable=True)
    revenue = Column(Numeric(16, 2), nullable=False, default=0)
    cost = Column(Numeric(16, 2), nullable=False, default=0)
    gross_profit = Column(Numeric(16, 2), nullable=False, default=0)
    ad_fee = Column(Numeric(16, 2), nullable=False, default=0)
    platform_fee = Column(Numeric(16, 2), nullable=False, default=0)
    tax_fee = Column(Numeric(16, 2), nullable=False, default=0)
    logistics_fee = Column(Numeric(16, 2), nullable=False, default=0)
    operating_profit = Column(Numeric(16, 2), nullable=False, default=0)
    order_count = Column(Integer, nullable=False, default=0)
    sales_qty = Column(Integer, nullable=False, default=0)

