"""
Product model - 商品主表.
Stores SKU basic information.
"""

import uuid
from sqlalchemy import Column, String, Numeric, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Product(Base):
    """商品主表 - SKU basic information."""

    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), nullable=False, unique=True, index=True, comment="SKU编码")
    product_name = Column(String(300), nullable=False, comment="产品名称")
    category = Column(String(100), nullable=True, comment="分类")
    brand = Column(String(100), nullable=True, comment="品牌")
    supplier = Column(String(200), nullable=True, comment="供应商")
    unit_cost = Column(Numeric(14, 4), nullable=True, comment="单件成本")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/discontinued")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
