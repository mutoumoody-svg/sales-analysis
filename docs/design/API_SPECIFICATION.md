# API SPECIFICATION

# API接口设计规范 V1.0


## 基础地址


/api/v1



---

# 1. 数据导入


## 上传订单


POST


/import/orders


功能：

上传销售订单文件。


输入：

Excel/CSV


输出：


{
success:true,

records:1000

}



---

# 2. 销售分析


GET


/sales/summary



返回：


销售额

订单数量

增长率



---

# 3. 利润分析


GET


/profit/summary



返回：


revenue

cost

gross_profit

net_profit

margin



---

# 4. 店铺利润


GET


/profit/store/{id}



返回：


店铺销售

成本

利润

利润率



---

# 5. SKU利润


GET


/profit/sku/{sku}



返回：


销量

收入

成本

利润



---

# 6. 库存分析


GET


/inventory/health



返回：


库存评分

风险SKU



---

# 7. AI建议


GET


/ai/recommendations



返回：


风险

机会

建议动作



---

# API原则


所有接口：

必须返回JSON。


必须包含：

status

data

message


