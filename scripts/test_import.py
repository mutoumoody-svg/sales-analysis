r"""
旺店通数据导入测试脚本
=====================
使用实际的旺店通导出文件测试导入功能。

用法:
    cd backend
    .venv\Scripts\python.exe scripts\test_import.py
"""

import sys
import os

# 确保能导入 backend 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal
from app.services.import_service import (
    import_sales_detail,
    import_returns_detail,
    import_inventory,
)


def main():
    # 数据文件路径
    sales_returns_file = r"C:\Users\jingz\Desktop\IMAX慕咖Sttoke礼盒装销售出库退货明细.xlsx"
    inventory_file = r"C:\Users\jingz\Downloads\库存整理_2026-07-10.xlsx"

    db = SessionLocal()

    try:
        # 1. 导入销售明细
        print("=" * 60)
        print("[1/3] 导入销售明细...")
        print("=" * 60)
        if os.path.exists(sales_returns_file):
            result = import_sales_detail(db, sales_returns_file, sheet_name="销售明细")
            print(result)
        else:
            print(f"文件不存在: {sales_returns_file}")

        # 2. 导入退货明细
        print()
        print("=" * 60)
        print("[2/3] 导入退货明细...")
        print("=" * 60)
        if os.path.exists(sales_returns_file):
            result = import_returns_detail(db, sales_returns_file, sheet_name="退货明细")
            print(result)
        else:
            print(f"文件不存在: {sales_returns_file}")

        # 3. 导入库存
        print()
        print("=" * 60)
        print("[3/3] 导入库存文件...")
        print("=" * 60)
        if os.path.exists(inventory_file):
            result = import_inventory(db, inventory_file, snapshot_date="2026-07-10")
            print(result)
        else:
            print(f"文件不存在: {inventory_file}")

        # 4. 验证数据库
        print()
        print("=" * 60)
        print("[验证] 数据库数据量统计")
        print("=" * 60)
        from sqlalchemy import text

        tables = [
            "stores",
            "products",
            "customers",
            "orders",
            "order_items",
            "inventory",
        ]
        for t in tables:
            r = db.execute(text(f"SELECT count(*) FROM {t}"))
            count = r.fetchone()[0]
            print(f"  {t:20s}: {count:6d} rows")

        # 5. 抽样验证
        print()
        print("=" * 60)
        print("[验证] 抽样数据")
        print("=" * 60)

        # 店铺列表
        r = db.execute(text("SELECT store_name, platform FROM stores ORDER BY store_name"))
        stores = r.fetchall()
        print(f"\n店铺 ({len(stores)}):")
        for s in stores:
            print(f"  - {s[0]}  [{s[1]}]")

        # 商品列表（前10个）
        r = db.execute(
            text("SELECT sku, product_name, brand FROM products ORDER BY sku LIMIT 10")
        )
        products = r.fetchall()
        print(f"\n商品 (前10/{len(products)}):")
        for p in products:
            print(f"  - {p[0]:15s}  {p[1][:30]:30s}  [{p[2] or ''}]")

        # 订单统计
        r = db.execute(
            text(
                "SELECT sales_type, count(*), sum(total_amount) "
                "FROM orders GROUP BY sales_type ORDER BY sales_type"
            )
        )
        orders = r.fetchall()
        print(f"\n订单按类型统计:")
        for o in orders:
            print(f"  - {o[0]:15s}  {o[1]:6d} orders  total: {o[2] or 0:.2f}")

        print()
        print("=" * 60)
        print("导入测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
