"""
Profit Calculation Service - 利润计算引擎.

Profit layers:
1. Gross Profit = Revenue - Product Cost
2. Contribution Profit = Gross Profit - (Shipping Cost + Packaging Cost + Variable Expenses)
3. Net Profit = Contribution Profit - Fixed Costs

Business rules:
- Never calculate profit with 0 cost (Cost Missing must be flagged)
- All calculations must be traceable
- Results stored in profit_analysis table (separate from raw data)
- If order.gross_profit is available (from import), use it directly instead of recomputing
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict
from datetime import date
from decimal import Decimal

from app.models.order import Order, OrderItem
from app.models.expense import Expense
from app.models.profit_analysis import ProfitAnalysis
from app.services.cost_service import get_unit_cost, CostMissingError


def calculate_profit_for_order(
    db: Session,
    order: Order,
) -> Dict:
    """Calculate profit for a single order.

    Priority:
    1. If order.gross_profit is not None (from import), use it directly
    2. Otherwise, compute from items + cost_service

    Returns a dict with:
    - revenue, cost, gross_profit
    - expenses breakdown
    - contribution_profit
    - cost_missing: list of items with missing costs
    """
    total_revenue = Decimal(str(order.total_amount))

    # Check if gross_profit was imported from the source data
    if order.gross_profit is not None:
        gross_profit = Decimal(str(order.gross_profit))
        # Estimate cost from revenue - gross_profit
        total_cost = total_revenue - gross_profit
        cost_missing_items = []
    else:
        # Compute from items using cost_service
        total_cost = Decimal("0")
        cost_missing_items = []

        for item in order.items:
            try:
                unit_cost = get_unit_cost(
                    db,
                    product_id=str(item.product_id),
                    store_id=str(order.store_id),
                    order_date=order.order_date,
                )
                item_cost = unit_cost * item.quantity
                total_cost += item_cost
            except CostMissingError:
                cost_missing_items.append({
                    "order_no": order.order_no,
                    "product_id": str(item.product_id),
                    "quantity": item.quantity,
                })

        gross_profit = total_revenue - total_cost

    # Order-level variable costs (from import data)
    shipping_cost = Decimal(str(order.shipping_cost or 0))
    packaging_cost = Decimal(str(order.packaging_cost or 0))

    # Get additional expenses from expense table (if available)
    expenses = (
        db.query(Expense)
        .filter(
            and_(
                Expense.store_id == order.store_id,
                Expense.date == order.order_date,
            )
        )
        .all()
    )

    expense_breakdown = {}
    total_variable_expenses = Decimal("0")
    total_fixed_expenses = Decimal("0")

    # Include order-level costs in expense breakdown
    if shipping_cost > 0:
        expense_breakdown["shipping_cost"] = shipping_cost
    if packaging_cost > 0:
        expense_breakdown["packaging_cost"] = packaging_cost

    for exp in expenses:
        exp_amount = Decimal(str(exp.amount))
        expense_breakdown[exp.expense_type] = expense_breakdown.get(exp.expense_type, Decimal("0")) + exp_amount

        if exp.expense_type == "Fixed":
            total_fixed_expenses += exp_amount
        else:
            total_variable_expenses += exp_amount

    # Contribution profit = Gross profit - variable costs (shipping + packaging + other variable)
    total_variable_costs = shipping_cost + packaging_cost + total_variable_expenses
    contribution_profit = gross_profit - total_variable_costs

    # Net profit = Contribution profit - fixed expenses
    net_profit = contribution_profit - total_fixed_expenses

    return {
        "order_no": order.order_no,
        "order_date": order.order_date,
        "store_id": str(order.store_id),
        "revenue": total_revenue,
        "cost": total_cost,
        "gross_profit": gross_profit,
        "expense_breakdown": {k: float(v) for k, v in expense_breakdown.items()},
        "contribution_profit": contribution_profit,
        "net_profit": net_profit,
        "cost_missing": cost_missing_items,
    }


def save_profit_analysis(
    db: Session,
    order: Order,
    profit_result: Dict,
) -> None:
    """Save profit calculation results to profit_analysis table.

    Uses order.gross_profit when available (from import).
    Applies order-level costs (shipping_cost, packaging_cost) proportionally to items.
    """
    # Get order-level variable costs
    shipping_cost = Decimal(str(order.shipping_cost or 0))
    packaging_cost = Decimal(str(order.packaging_cost or 0))
    total_variable_cost = shipping_cost + packaging_cost

    # Total item revenue for proportional allocation
    total_item_revenue = sum(Decimal(str(item.amount)) for item in order.items) or Decimal("1")

    for item in order.items:
        # Skip items with missing costs
        missing = any(m["product_id"] == str(item.product_id) for m in profit_result["cost_missing"])
        if missing:
            continue

        # Get item revenue and cost
        item_revenue = Decimal(str(item.amount))

        if order.gross_profit is not None:
            # Use imported cost data
            item_cost = Decimal(str(item.total_cost)) if item.total_cost else Decimal("0")
            item_gross = item_revenue - item_cost
        else:
            # Compute via cost_service
            try:
                unit_cost = get_unit_cost(
                    db,
                    product_id=str(item.product_id),
                    store_id=str(order.store_id),
                    order_date=order.order_date,
                )
            except CostMissingError:
                continue
            item_cost = unit_cost * item.quantity
            item_gross = item_revenue - item_cost

        # Proportionally allocate order-level variable costs
        proportion = item_revenue / total_item_revenue
        item_variable_cost = total_variable_cost * proportion
        item_contribution = item_gross - item_variable_cost
        item_net = item_contribution  # No fixed cost allocation yet

        record = ProfitAnalysis(
            date=order.order_date,
            store_id=order.store_id,
            product_id=item.product_id,
            revenue=item_revenue,
            cost=item_cost,
            gross_profit=item_gross,
            contribution_profit=item_contribution,
            net_profit=item_net,
        )
        db.add(record)

    db.commit()
