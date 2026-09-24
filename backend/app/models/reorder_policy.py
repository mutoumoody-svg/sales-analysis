"""Per-SKU ordering policy overrides used by the reorder engine."""

import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ReorderPolicy(Base):
    __tablename__ = "reorder_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, unique=True, index=True)
    lead_time_days = Column(Integer, nullable=False, default=60)
    review_period_days = Column(Integer, nullable=False, default=30)
    safety_days = Column(Integer, nullable=True)
    min_order_qty = Column(Integer, nullable=False, default=1)
    order_multiple = Column(Integer, nullable=False, default=1)
    max_stock_days = Column(Integer, nullable=False, default=180)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
