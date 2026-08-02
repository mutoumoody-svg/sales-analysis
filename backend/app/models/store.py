"""
Store model - 店铺表.
Represents sales channels (e.g., Tmall flagship store, JD official store).
"""

import uuid
from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Store(Base):
    """店铺表 - stores sales channel information."""

    __tablename__ = "stores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_name = Column(String(200), nullable=False, index=True, comment="店铺名称")
    platform = Column(String(50), nullable=False, comment="平台: 天猫/京东/抖音/等")
    channel = Column(String(50), nullable=True, comment="渠道分类")
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
