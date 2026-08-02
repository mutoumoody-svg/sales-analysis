"""
Order and OrderItem models - 订单主表 + 订单明细表.
"""

import uuid
from sqlalchemy import Column, String, Date, Numeric, Integer, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Order(Base):
    """订单主表 - order header information."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no = Column(String(100), nullable=False, unique=True, index=True, comment="订单编号")
    order_date = Column(Date, nullable=False, index=True, comment="订单日期")
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False, index=True, comment="店铺")
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, comment="客户")
    sales_type = Column(String(20), nullable=False, default="Retail", comment="销售类型: Retail/Wholesale/Promotion/Clearance/Sample/Return")
    total_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="订单支付金额")
    discount = Column(Numeric(14, 2), nullable=False, default=0, comment="订单总优惠")
    shipping_fee = Column(Numeric(14, 2), nullable=False, default=0, comment="邮费")
    shipping_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="邮资成本")
    packaging_cost = Column(Numeric(14, 2), nullable=False, default=0, comment="订单包装成本")
    gross_profit = Column(Numeric(14, 2), nullable=True, comment="订单毛利")
    gross_profit_rate = Column(Numeric(8, 4), nullable=True, comment="毛利率")

    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    store = relationship("Store")
    customer = relationship("Customer")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


class OrderItem(Base):
    """订单明细表 - individual product lines within an order."""

    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True, comment="订单")
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True, comment="商品")
    quantity = Column(Integer, nullable=False, default=1, comment="数量")
    selling_price = Column(Numeric(14, 2), nullable=False, comment="货品成交价")
    amount = Column(Numeric(14, 2), nullable=False, comment="货品成交总价")
    unit_cost = Column(Numeric(14, 4), nullable=True, comment="货品成本(单价)")
    total_cost = Column(Numeric(14, 2), nullable=True, comment="货品总成本")
    warehouse = Column(String(100), nullable=True, comment="仓库")

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
