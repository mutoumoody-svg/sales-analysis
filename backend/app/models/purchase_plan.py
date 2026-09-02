"""Confirmable purchase plan generated from reorder recommendations."""

import uuid

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class PurchasePlan(Base):
    __tablename__ = "purchase_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True, index=True)
    period = Column(String(7), nullable=False, index=True)
    suggested_qty = Column(Integer, nullable=False)
    confirmed_qty = Column(Integer, nullable=True)
    unit_cost = Column(Numeric(14, 4), nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    priority = Column(String(20), nullable=False, default="normal")
    source = Column(String(50), nullable=False, default="reorder_engine")
    notes = Column(Text, nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    confirmed_at = Column(TIMESTAMP, nullable=True)
    expected_date = Column(Date, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
