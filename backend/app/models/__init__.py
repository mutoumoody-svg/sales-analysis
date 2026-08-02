"""
Database models package.
Import all models here so they are registered with SQLAlchemy Base.
"""

from app.models.store import Store
from app.models.product import Product
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.sku_cost import SkuCost
from app.models.inventory import Inventory
from app.models.expense import Expense
from app.models.profit_analysis import ProfitAnalysis
from app.models.ai_recommendation import AIRecommendation
from app.models.sales_summary import SalesSummary

__all__ = [
    "Store",
    "Product",
    "Customer",
    "Order",
    "OrderItem",
    "SkuCost",
    "Inventory",
    "Expense",
    "ProfitAnalysis",
    "AIRecommendation",
    "SalesSummary",
]
