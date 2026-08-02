"""
Sales Classification Service - 销售分类服务.

Business rules:
1. If customer_type = Distributor -> Wholesale
2. If channel = flagship/official/e-commerce -> Retail (default)
3. If quantity abnormally large -> Potential Wholesale (flagged for review)

Types: Retail / Wholesale / Promotion / Clearance / Sample
"""

from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

# Threshold for "abnormally large" quantity (configurable)
LARGE_QUANTITY_THRESHOLD = 50


def classify_sales_type(
    customer_type: Optional[str],
    store_channel: Optional[str],
    total_quantity: int,
    total_amount: Decimal,
) -> str:
    """Determine sales type based on business rules.

    Args:
        customer_type: Normal / Dealer / Distributor
        store_channel: store's channel classification
        total_quantity: total items in order
        total_amount: order total amount

    Returns:
        One of: Retail / Wholesale / Promotion / Clearance / Sample / Potential Wholesale
    """
    # Rule 1: Distributor customer -> Wholesale
    if customer_type == "Distributor":
        return "Wholesale"

    # Rule 2: Flagship/official/e-commerce -> Retail (default)
    if store_channel in ("flagship", "official", "e-commerce", "旗舰店", "官方店"):
        # Rule 3: Check for abnormally large quantity
        if total_quantity >= LARGE_QUANTITY_THRESHOLD:
            return "Potential Wholesale"
        return "Retail"

    # Default: Retail
    if total_quantity >= LARGE_QUANTITY_THRESHOLD:
        return "Potential Wholesale"

    return "Retail"
