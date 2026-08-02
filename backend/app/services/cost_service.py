"""
Cost Matching Service - 成本匹配引擎.

Implements the cost priority chain:
1. Store-specific cost (店铺专属成本)
2. Channel cost (渠道成本)
3. SKU standard cost (标准成本)
4. Default cost (默认成本)

If no cost found: mark as 'Cost Missing' (never use 0 cost).
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date
from decimal import Decimal

from app.models.sku_cost import SkuCost
from app.models.product import Product
from app.models.store import Store


class CostMissingError(Exception):
    """Raised when no cost is found for a SKU."""
    pass


def get_unit_cost(
    db: Session,
    product_id: str,
    store_id: str,
    order_date: date,
) -> Decimal:
    """Get the unit cost for a product at a specific store.

    Priority:
    1. Store-specific cost (cost_type='store', store_id matches)
    2. Channel cost (cost_type='channel', based on store's channel)
    3. SKU standard cost (cost_type='standard', store_id is NULL)
    4. Default cost (cost_type='default')

    Returns the unit cost as Decimal.
    Raises CostMissingError if no cost is found.
    """
    # Priority 1: Store-specific cost
    store_cost = (
        db.query(SkuCost)
        .filter(
            and_(
                SkuCost.product_id == product_id,
                SkuCost.store_id == store_id,
                SkuCost.cost_type == "store",
                SkuCost.effective_date <= order_date,
            )
        )
        .order_by(SkuCost.effective_date.desc())
        .first()
    )
    if store_cost:
        return store_cost.unit_cost

    # Priority 2: Channel cost
    store = db.query(Store).filter(Store.id == store_id).first()
    if store and store.channel:
        channel_cost = (
            db.query(SkuCost)
            .filter(
                and_(
                    SkuCost.product_id == product_id,
                    SkuCost.cost_type == "channel",
                    SkuCost.effective_date <= order_date,
                )
            )
            .order_by(SkuCost.effective_date.desc())
            .first()
        )
        if channel_cost:
            return channel_cost.unit_cost

    # Priority 3: SKU standard cost (store_id is NULL)
    standard_cost = (
        db.query(SkuCost)
        .filter(
            and_(
                SkuCost.product_id == product_id,
                SkuCost.store_id.is_(None),
                SkuCost.cost_type == "standard",
                SkuCost.effective_date <= order_date,
            )
        )
        .order_by(SkuCost.effective_date.desc())
        .first()
    )
    if standard_cost:
        return standard_cost.unit_cost

    # Priority 4: Default cost
    default_cost = (
        db.query(SkuCost)
        .filter(
            and_(
                SkuCost.product_id == product_id,
                SkuCost.cost_type == "default",
                SkuCost.effective_date <= order_date,
            )
        )
        .order_by(SkuCost.effective_date.desc())
        .first()
    )
    if default_cost:
        return default_cost.unit_cost

    # No cost found - NEVER use 0 cost
    raise CostMissingError(
        f"No cost found for product_id={product_id}, store_id={store_id}, date={order_date}. "
        "Marking as 'Cost Missing'. Never calculate profit with 0 cost."
    )
