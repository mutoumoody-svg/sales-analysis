#!/usr/bin/env python3
"""一次性重算：用系统成本(products.unit_cost)覆盖旺店通导入的成本/毛利。

执行后，sales_summary 与 orders 的所有成本/利润字段均以系统成本为准
（缺系统成本的行/单保留原导入值）。输出缺成本 SKU 清单供补录。
"""
import sys
from pathlib import Path

# 支持从项目根目录或 server app 目录运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.services.system_cost_service import (
    recalc_order_items_cost,
    recalc_orders_gross_profit,
    recalc_sales_summary,
    list_missing_cost_skus,
)


def main():
    db = SessionLocal()
    try:
        print("== 1. 重算 order_items 成本（系统成本覆盖）==")
        n1 = recalc_order_items_cost(db)
        print(f"   更新 {n1} 条明细")

        print("== 2. 重算 orders.gross_profit（订单毛利）==")
        n2 = recalc_orders_gross_profit(db)
        print(f"   更新 {n2} 个订单")

        print("== 3. 重算 sales_summary 成本/利润（店铺×SKU×月份）==")
        n3 = recalc_sales_summary(db)
        print(f"   更新 {n3} 行")

        print("\n== 4. 缺系统成本的 SKU（需在系统补录 unit_cost）==")
        missing = list_missing_cost_skus(db)
        if not missing:
            print("   全部 SKU 均有系统成本，无遗漏")
        else:
            print(f"   共 {len(missing)} 个 SKU 缺系统成本：")
            print(f"   {'SKU':<25} {'产品名':<20} {'销售金额':>12} {'数量':>6} 最近月份")
            for m in missing:
                print(f"   {m['sku']:<25} {(m['product_name'] or '')[:20]:<20} "
                      f"{m['net_amount']:>12,.2f} {m['net_qty']:>6} {m['last_period']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
