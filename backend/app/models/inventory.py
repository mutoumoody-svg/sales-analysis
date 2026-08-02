"""
Inventory model - 库存表.
Supports inventory health analysis.
"""

import uuid
from sqlalchemy import Column, String, Integer, Date, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Inventory(Base):
    """库存表 - current stock levels per SKU per warehouse.

    Effective inventory = available_qty + inbound_qty - reserved_qty
    """

    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, comment="商品")
    warehouse = Column(String(100), nullable=False, default="default", comment="仓库")
    available_qty = Column(Integer, nullable=False, default=0, comment="可售库存")
    reserved_qty = Column(Integer, nullable=False, default=0, comment="预留库存")
    inbound_qty = Column(Integer, nullable=False, default=0, comment="在途库存")
    date = Column(Date, nullable=False, index=True, comment="日期")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
