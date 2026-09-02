# DATA IMPORT TEMPLATE

# AI 企业经营决策平台数据导入规范 V1.0


## 1. 目的


定义系统第一阶段的数据输入标准。


支持：

- Excel
- CSV
- ERP导出文件
- 电商平台数据


目标：

将不同来源的数据转换为统一业务模型。


---

# 2. 数据导入流程


原始数据

↓

数据清洗

↓

字段映射

↓

业务规则处理

↓

分析计算

↓

Dashboard



---

# 3. 第一阶段必须数据


MVP阶段需要：

1. 销售订单数据

2. 商品SKU数据

3. 店铺数据

4. 成本数据

5. 库存数据


---

# 4. 销售订单数据

文件：

orders.xlsx


## 字段定义


|字段|是否必须|说明|
|-|-|-|
|order_id|必须|订单编号|
|order_date|必须|订单日期|
|store_name|必须|销售店铺|
|customer_name|可选|客户名称|
|customer_type|可选|客户分类|
|sku|必须|产品SKU|
|product_name|必须|产品名称|
|quantity|必须|销售数量|
|sales_amount|必须|销售金额|
|discount|可选|优惠金额|
|platform_fee|可选|平台费用|
|shipping_fee|可选|物流费用|



---

# 5. 商品SKU数据

文件：

products.xlsx


字段：


|字段|说明|
|-|-|
|sku|SKU编码|
|product_name|产品名称|
|category|分类|
|brand|品牌|
|supplier|供应商|
|status|状态|



---

# 6. 店铺数据

文件：

stores.xlsx


字段：


|字段|说明|
|-|-|
|store_name|店铺名称|
|platform|平台|
|channel|渠道|
|store_type|类型|



示例：


|店铺|平台|
|-|-|
|木卡旗舰店|天猫|
|木卡官方店|京东|



---

# 7. 成本数据

文件：

sku_costs.xlsx


核心：

支持同SKU不同店铺成本。


字段：


|字段|说明|
|-|-|
|sku|SKU|
|store_name|店铺|
|unit_cost|单位成本|
|effective_date|生效日期|



示例：


|SKU|店铺|成本|
|-|-|-|
|A001|天猫|18|
|A001|京东|20|
|A001|抖音|22|



---

# 8. 库存数据

文件：

inventory.xlsx


字段：


|字段|说明|
|-|-|
|sku|SKU|
|warehouse|仓库|
|available_qty|可售库存|
|reserved_qty|锁定库存|
|inbound_qty|在途库存|
|inventory_date|日期|



---

# 9. 销售类型字段


系统自动生成：

sales_type


类型：


Retail

零售


Wholesale

批发


Promotion

促销


Clearance

清仓


Sample

样品



---

# 10. 自动分类规则


## 经销商


如果：

customer_type = Dealer


则：

sales_type = Wholesale



---

## 电商零售


如果：

store_type = Online Store


默认：

sales_type = Retail



---

## 大订单识别


如果：

quantity > 正常订单阈值


标记：

Potential Wholesale



---

# 11. 数据质量检查


导入前检查：


## SKU检查


必须存在SKU。


不存在：

Error



---

## 成本检查


没有成本：

Cost Missing



禁止：

使用0成本计算利润。



---

## 日期检查


订单日期必须有效。



---

# 12. 第一版导入目标


输入：

一个月销售数据


输出：


销售分析


利润分析


SKU利润排名


店铺利润排名


库存资金占用


AI经营建议



---

# 13. 后续扩展


未来增加：


广告数据

采购数据

财务数据

客户生命周期数据

供应链数据



---

# Version

V1.0

Date:

2026-08-01
