"""诊断脚本：检查旺店通数据字段类型和导入错误"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pandas as pd
from app.services import field_mapping as fm

f = r"C:\Users\jingz\Desktop\IMAX慕咖Sttoke礼盒装销售出库退货明细.xlsx"
df = pd.read_excel(f, sheet_name="销售明细", nrows=5)

# Check data types
for idx, row in df.iterrows():
    rd = row.to_dict()
    print(f"--- Row {idx} ---")
    for key in ["订单编号", "店铺", "商家编码", "货品名称", "下单时间", "订单类型", "货品数量", "货品成交价", "货品成交总价", "订单支付金额"]:
        val = rd.get(key)
        print(f"  {key}: [{val}] type={type(val).__name__}")
    print()

# Test the import on first 3 rows
print("=" * 60)
print("Testing import on first 3 rows...")
print("=" * 60)

from app.database import SessionLocal
from app.services.import_service import import_sales_detail, ImportResult
from sqlalchemy import text

# Save first 3 rows to temp file
import tempfile
tmp = tempfile.mktemp(suffix=".xlsx")
df.head(3).to_excel(tmp, index=False, sheet_name="销售明细")

db = SessionLocal()
try:
    result = import_sales_detail(db, tmp, sheet_name="销售明细")
    print(result)
    print()
    print("Errors (first 5):")
    for e in result.errors[:5]:
        print(f"  {e}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
    os.remove(tmp)
