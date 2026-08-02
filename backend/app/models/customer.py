"""
Customer model - 客户表.
Distinguishes retail customers from wholesale customers.
"""

import uuid
from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Customer(Base):
    """客户表 - customer classification (Normal / Dealer / Distributor)."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String(200), nullable=True, comment="客户名称")
    customer_type = Column(String(30), nullable=False, default="Normal", comment="类型: Normal/Dealer/Distributor")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
