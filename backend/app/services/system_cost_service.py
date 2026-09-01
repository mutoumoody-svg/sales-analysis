"""
System Cost Service - 系统成本统一应用.

全系统成本口径：利润计算一律使用系统内维护的成本（products.unit_cost），
不使用旺店通等外部导入的成本。外部成本仅在 SKU 缺系统成本时作为回退。

提供：
1. recalc_order_items_cost()   - 用系统成本覆盖 order_items 的成本字段
2. recalc_orders_gross_profit() - 重算订单毛利（total_amount - Σ系统成本）
3. recalc_sales_summary()       - 用系统成本重算 sales_summary 的成本/利润字段
4. list_missing_cost_skus()     - 列出有销售但缺系统成本的 SKU（需补录）
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def recalc_order_items_cost(db: Session) -> int:
    """用系统成本覆盖 order_items.unit_cost / total_cost。

    仅覆盖 products.unit_cost > 0 的商品；其余保留原（旺店通）成本。
    返回更新行数。
    """
    result = db.execute(text("""
        UPDATE order_items oi
        SET unit_cost = p.unit_cost,
            total_cost = ROUND(p.unit_cost * oi.quantity, 2)
        FROM products p
        WHERE p.id = oi.product_id AND p.unit_cost > 0
    """))
    db.commit()
    return result.rowcount


def recalc_orders_gross_profit(db: Session, order_ids: list | None = None) -> int:
    """重算订单毛利：gross_profit = total_amount - Σ(明细成本)。

    明细成本已是"系统成本优先"口径（recalc_order_items_cost 覆盖后）。
    仅重算所有明细都有成本的订单；有明细缺成本的订单保留原毛利。
    order_ids 为空时全量重算。返回更新行数。
    """
    where_clause = ""
    params = {}
    if order_ids:
        where_clause = "AND s.order_id = ANY(:ids)"
        params["ids"] = list(order_ids)

    result = db.execute(text(f"""
        UPDATE orders o
        SET gross_profit = ROUND(o.total_amount - s.cost, 2),
            gross_profit_rate = ROUND((o.total_amount - s.cost)
                / NULLIF(o.total_amount, 0), 4)
        FROM (
            SELECT oi.order_id, SUM(oi.total_cost) AS cost
            FROM order_items oi
            GROUP BY oi.order_id
            HAVING COUNT(*) FILTER (WHERE oi.total_cost IS NULL) = 0
        ) s
        WHERE o.id = s.order_id {where_clause}
    """), params)
    db.commit()
    return result.rowcount


def recalc_sales_summary(db: Session) -> int:
    """用系统成本重算 sales_summary 的成本/利润字段。

    口径（与导入表原公式一致）：
      total_cost  = unit_cost × ship_qty
      return_cost = unit_cost × return_qty
      net_cost    = unit_cost × net_qty
      ship_profit = ship_amount - total_cost
      net_profit  = net_amount - net_cost
    仅重算 products.unit_cost > 0 的行；其余保留原导入值。
    返回更新行数。
    """
    result = db.execute(text("""
        UPDATE sales_summary ss
        SET total_cost  = ROUND(p.unit_cost * ss.ship_qty, 2),
            return_cost = ROUND(p.unit_cost * ss.return_qty, 2),
            net_cost    = ROUND(p.unit_cost * ss.net_qty, 2),
            ship_profit = ROUND(ss.ship_amount - p.unit_cost * ss.ship_qty, 2),
            net_profit  = ROUND(ss.net_amount - p.unit_cost * ss.net_qty, 2)
        FROM products p
        WHERE p.id = ss.product_id AND p.unit_cost > 0
    """))
    db.commit()
    return result.rowcount


def list_missing_cost_skus(db: Session, period: str | None = None) -> list[dict]:
    """列出有销售记录但缺系统成本(unit_cost<=0 或 NULL)的 SKU，按销售额降序。"""
    period_filter = "AND ss.period = :period" if period else ""
    params = {"period": period} if period else {}
    rows = db.execute(text(f"""
        SELECT p.sku, p.product_name,
               SUM(ss.net_amount) AS net_amount,
               SUM(ss.net_qty) AS net_qty,
               MAX(ss.period) AS last_period
        FROM sales_summary ss
        JOIN products p ON p.id = ss.product_id
        WHERE (p.unit_cost IS NULL OR p.unit_cost <= 0) {period_filter}
        GROUP BY p.sku, p.product_name
        HAVING SUM(ss.net_amount) > 0
        ORDER BY SUM(ss.net_amount) DESC
    """), params).fetchall()
    return [
        {
            "sku": r.sku,
            "product_name": r.product_name,
            "net_amount": float(r.net_amount),
            "net_qty": int(r.net_qty),
            "last_period": r.last_period,
        }
        for r in rows
    ]
