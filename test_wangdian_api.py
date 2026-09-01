#!/usr/bin/env python3
"""测试旺店通API连通性 - 拉取最近1天库存（凭证从环境变量读取）"""
import os
import sys
sys.path.insert(0, "/home/ubuntu/sales-analysis")

from app.services.wangdian_client import WangdianClient
from datetime import datetime, timedelta

client = WangdianClient(
    sid=os.environ.get("WANGDIAN_SID", ""),
    appkey=os.environ.get("WANGDIAN_APPKEY", ""),
    appsecret=os.environ.get("WANGDIAN_APPSECRET", ""),
)

now = datetime.now()
start = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
end = now.strftime("%Y-%m-%d %H:%M:%S")
print(f"测试拉取: {start} ~ {end}")

stocks, total = client.query_all_stock(start_time=start, end_time=end, page_size=100)
print(f"总记录数: {total}")
print(f"实际拉取: {len(stocks)} 条")

if stocks:
    print("第一条示例:")
    s = stocks[0]
    for k in ["spec_no", "goods_name", "warehouse_name", "stock_num", "lock_num", "modified"]:
        print(f"  {k}: {s.get(k)}")
    print(f"所有字段: {list(s.keys())}")

    # 统计仓库
    warehouses = set()
    for s in stocks:
        warehouses.add(s.get("warehouse_name", "未知"))
    print(f"仓库列表: {warehouses}")
