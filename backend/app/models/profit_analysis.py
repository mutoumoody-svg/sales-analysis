"""
Profit Analysis model - 利润分析结果表.
Stores calculated profit results (separate from raw data).
"""

import uuid
from sqlalchemy import Column, Date, Numeric, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class ProfitAnalysis(Base):
    """利润分析结果表 - calculated profit by date/store/product.

    Profit layers:
    - revenue             (销售收入)
    - cost                (产品成本)
    - gross_profit        (毛利 = revenue - cost)
    - contribution_profit (贡献利润 = gross_profit - expenses)
    - net_profit          (净利润 = contribution_profit - fixed costs)
    """

    __tablename__ = "profit_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False, index=True, comment="日期")
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True, comment="店铺")
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, comment="商品")
    revenue = Column(Numeric(14, 2), nullable=False, default=0, comment="销售收入")
    cost = Column(Numeric(14, 2), nullable=False, default=0, comment="产品成本")
    gross_profit = Column(Numeric(14, 2), nullable=False, default=0, comment="毛利")
    contribution_profit = Column(Numeric(14, 2), nullable=False, default=0, comment="贡献利润")
    net_profit = Column(Numeric(14, 2), nullable=False, default=0, comment="净利润")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
