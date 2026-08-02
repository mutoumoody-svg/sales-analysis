"""
SalesSummary model - 货品销售汇总表.
按 店铺×货品 维度的销售汇总，来自旺店通货品销售汇总表导出。
"""

import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SalesSummary(Base):
    """货品销售汇总表 - store x product level summary.

    Source: 旺店通 > 货品销售汇总表
    Contains: 发货/退货/实际销售 的数量、金额、成本、利润
    """

    __tablename__ = "sales_summary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 维度
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True, comment="店铺")
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, comment="商品")
    period = Column(String(7), nullable=False, default="2026-07", index=True, comment="会计期间 YYYY-MM")

    # 数量
    ship_qty = Column(Integer, nullable=False, default=0, comment="发货总量")
    return_qty = Column(Integer, nullable=False, default=0, comment="退货总量")
    net_qty = Column(Integer, nullable=False, default=0, comment="实际销售量")
    unshipped_refund_qty = Column(Integer, nullable=False, default=0, comment="未发货退款数量")
    gift_qty = Column(Integer, nullable=False, default=0, comment="赠品数量")

    # 金额
    avg_price = Column(Numeric(14, 4), nullable=True, comment="均价")
    ship_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="发货总金额")
    return_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="退货总金额")
    net_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="实际销售额")
    unshipped_refund_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="未发货退款金额")

    # 成本
    total_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="货品总成本")
    return_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="退货总成本")
    net_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="实际总成本")
    commission_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="佣金成本")
    unknown_cost_sales = Column(Numeric(14, 2), nullable=False, default=0, comment="未知成本销售总额")

    # 利润
    ship_profit = Column(Numeric(14, 2), nullable=False, default=0, comment="货品总利润(发货)")
    net_profit = Column(Numeric(14, 2), nullable=False, default=0, comment="实际总利润")

    # 唯一约束：同一店铺+商品+月份只有一条汇总
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", "period", name="uq_sales_summary_store_product_period"),
    )

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
