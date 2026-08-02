r"""
旺店通数据导入测试脚本 v2
=========================
使用新的数据结构文件测试导入功能。

数据文件:
  1. 销售出库明细表: D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx
  2. 货品销售汇总表: D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx
  3. 库存文件: C:\Users\jingz\Downloads\库存整理_2026-07-10.xlsx

用法:
    cd backend
    .venv\Scripts\python.exe ..\scripts\test_import_v2.py
"""

import sys
import os

# 确保能找到 app 包
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_dir))

from app.database import SessionLocal
from app.services.import_service import (
    import_sales_detail,
    import_sales_summary,
    import_inventory,
)

# 数据文件路径
DETAIL_FILE = r"D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx"
SUMMARY_FILE = r"D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx"
INVENTORY_FILE = r"C:\Users\jingz\Downloads\库存整理_2026-07-10.xlsx"


def main():
    db = SessionLocal()

    try:
        # ===== 1. 销售出库明细表 =====
        print("=" * 70)
        print("1. 导入销售出库明细表")
        print("=" * 70)
        if os.path.exists(DETAIL_FILE):
            result = import_sales_detail(db, DETAIL_FILE, sheet_name="Sheet1")
            print(result)
            print()
        else:
            print(f"  文件不存在: {DETAIL_FILE}")

        # ===== 2. 货品销售汇总表 =====
        print("=" * 70)
        print("2. 导入货品销售汇总表")
        print("=" * 70)
        if os.path.exists(SUMMARY_FILE):
            result = import_sales_summary(db, SUMMARY_FILE, sheet_name="Sheet1")
            print(result)
            print()
        else:
            print(f"  文件不存在: {SUMMARY_FILE}")

        # ===== 3. 库存文件 =====
        print("=" * 70)
        print("3. 导入库存文件")
        print("=" * 70)
        if os.path.exists(INVENTORY_FILE):
            result = import_inventory(db, INVENTORY_FILE, snapshot_date="2026-07-10")
            print(result)
            print()
        else:
            print(f"  文件不存在: {INVENTORY_FILE}")

        # ===== 汇总 =====
        print("=" * 70)
        print("导入完成 - 数据库状态")
        print("=" * 70)

        from sqlalchemy import text
        tables = ["stores", "products", "customers", "orders", "order_items",
                  "sales_summary", "inventory"]
        for t in tables:
            r = db.execute(text(f"SELECT count(*) FROM {t}"))
            count = r.fetchone()[0]
            print(f"  {t:20s}: {count:>8,}")

        # 关键金额校验
        print()
        print("--- 金额校验 ---")
        r = db.execute(text("""
            SELECT
                count(*) as order_count,
                sum(total_amount) as total_payment,
                sum(gross_profit) as total_gross_profit,
                avg(gross_profit_rate) as avg_profit_rate
            FROM orders
        """))
        row = r.fetchone()
        print(f"  订单数: {row[0]:,}")
        print(f"  订单支付金额合计: {row[1]:,.2f}" if row[1] else "  订单支付金额合计: 0")
        print(f"  订单毛利合计: {row[2]:,.2f}" if row[2] else "  订单毛利合计: N/A")
        print(f"  平均毛利率: {row[3]:.4f}" if row[3] else "  平均毛利率: N/A")

        r = db.execute(text("""
            SELECT
                count(*) as item_count,
                sum(amount) as total_amount,
                sum(total_cost) as total_cost,
                sum(quantity) as total_qty
            FROM order_items
        """))
        row = r.fetchone()
        print(f"  明细数: {row[0]:,}")
        print(f"  成交金额合计: {row[1]:,.2f}" if row[1] else "  成交金额合计: 0")
        print(f"  货品总成本合计: {row[2]:,.2f}" if row[2] else "  货品总成本合计: N/A")
        print(f"  货品数量合计: {row[3]:,}" if row[3] else "  货品数量合计: 0")

        r = db.execute(text("""
            SELECT
                count(*) as summary_count,
                sum(ship_amount) as ship_total,
                sum(return_amount) as return_total,
                sum(net_amount) as net_total,
                sum(net_cost) as net_cost,
                sum(net_profit) as net_profit
            FROM sales_summary
        """))
        row = r.fetchone()
        if row and row[0] > 0:
            print()
            print("--- 汇总表校验 ---")
            print(f"  汇总记录数: {row[0]:,}")
            print(f"  发货总金额: {row[1]:,.2f}" if row[1] else "  发货总金额: 0")
            print(f"  退货总金额: {row[2]:,.2f}" if row[2] else "  退货总金额: 0")
            print(f"  实际销售额: {row[3]:,.2f}" if row[3] else "  实际销售额: 0")
            print(f"  实际总成本: {row[4]:,.2f}" if row[4] else "  实际总成本: 0")
            print(f"  实际总利润: {row[5]:,.2f}" if row[5] else "  实际总利润: 0")

        # 店铺分布
        print()
        print("--- 店铺分布 ---")
        r = db.execute(text("""
            SELECT s.store_name, s.platform, count(o.id) as orders, sum(o.total_amount) as amount
            FROM stores s
            LEFT JOIN orders o ON o.store_id = s.id
            GROUP BY s.store_name, s.platform
            ORDER BY amount DESC NULLS LAST
            LIMIT 15
        """))
        for row in r.fetchall():
            amt = f"{row[3]:,.2f}" if row[3] else "0"
            print(f"  {row[0]:30s} [{row[1]:6s}] {row[2]:>5} orders  {amt}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
