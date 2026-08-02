"""
SKU Cost model - SKU成本表.
Supports different costs for the same SKU across different stores.
This is a CORE table: same SKU can have different costs per store.
"""

import uuid
from sqlalchemy import Column, Date, Numeric, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SkuCost(Base):
    """SKU成本表 - supports same SKU, different store, different cost.

    Cost priority (handled in service layer):
    1. Store-specific cost (store_id is set)
    2. Channel cost
    3. SKU standard cost (store_id is NULL)
    4. Default cost
    """

    __tablename__ = "sku_costs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, comment="商品")
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=True, index=True, comment="店铺(NULL=标准成本)")
    cost_type = Column(String(30), nullable=False, default="standard", comment="成本类型: store/channel/standard/default")
    unit_cost = Column(Numeric(14, 4), nullable=False, comment="单位成本")
    effective_date = Column(Date, nullable=False, comment="生效日期")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
