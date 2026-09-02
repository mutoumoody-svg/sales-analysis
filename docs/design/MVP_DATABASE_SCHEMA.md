# MVP DATABASE SCHEMA

# AI 企业经营决策平台 MVP 数据库结构 V1.0


## 1. 数据库目标


第一阶段支持：

- 销售数据导入
- SKU利润计算
- 店铺利润分析
- 成本匹配
- 基础库存分析


数据库设计原则：

1. 数据可追溯

2. 业务逻辑清晰

3. 支持后续AI分析扩展



---

# 2. 数据库技术建议


MVP阶段：

Database:

PostgreSQL


原因：

- 稳定
- 支持复杂查询
- 适合分析系统



---

# 3. 核心数据表


## 3.1 stores

店铺表


用途：

保存销售渠道信息。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|store_name|varchar|店铺名称|
|platform|varchar|平台|
|channel|varchar|渠道|
|created_at|timestamp|创建时间|



示例：


|store_name|platform|
|-|-|
|木卡旗舰店|天猫|
|官方店|京东|



---

# 3.2 products

商品主表


用途：

保存SKU基础信息。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|sku|varchar|SKU编码|
|product_name|varchar|产品名称|
|category|varchar|分类|
|brand|varchar|品牌|
|supplier|varchar|供应商|
|status|varchar|状态|



---

# 3.3 customers

客户表


用途：

区分零售客户和批发客户。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|customer_name|varchar|客户名称|
|customer_type|varchar|客户类型|



customer_type:


Normal

Dealer

Distributor



---

# 3.4 orders

订单主表


用途：

保存订单基础信息。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|order_no|varchar|订单编号|
|order_date|date|订单日期|
|store_id|UUID|店铺|
|customer_id|UUID|客户|
|sales_type|varchar|销售类型|
|total_amount|decimal|订单金额|



---

# 3.5 order_items

订单明细表


用途：

记录订单中的具体商品。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|order_id|UUID|订单|
|product_id|UUID|商品|
|quantity|integer|数量|
|selling_price|decimal|销售单价|
|amount|decimal|销售金额|



关系：

一个订单：

多个商品。


---

# 3.6 sku_costs

SKU成本表


核心表。


用途：

支持：

同SKU不同店铺不同成本。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|product_id|UUID|商品|
|store_id|UUID|店铺|
|unit_cost|decimal|单位成本|
|effective_date|date|生效日期|



示例：


SKU001


天猫：

18元


京东：

20元



---

# 3.7 inventory

库存表


用途：

库存健康分析。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|product_id|UUID|商品|
|warehouse|varchar|仓库|
|available_qty|integer|可售库存|
|reserved_qty|integer|预留库存|
|inbound_qty|integer|在途库存|
|date|date|日期|



---

# 3.8 expenses

费用表


用途：

计算真实利润。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|store_id|UUID|店铺|
|expense_type|varchar|费用类型|
|amount|decimal|金额|
|date|date|日期|



expense_type:


Advertising

广告


Platform Fee

平台费用


Shipping

物流


Gift

赠品


Operation

运营



---

# 3.9 profit_analysis

利润分析结果表


用途：

保存计算结果。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|date|date|日期|
|store_id|UUID|店铺|
|product_id|UUID|SKU|
|revenue|decimal|销售收入|
|cost|decimal|产品成本|
|gross_profit|decimal|毛利|
|contribution_profit|decimal|贡献利润|
|net_profit|decimal|净利润|



---

# 3.10 ai_recommendations

AI建议表


用途：

保存AI输出。


字段：


|字段|类型|说明|
|-|-|-|
|id|UUID|主键|
|agent_type|varchar|Agent类型|
|target_type|varchar|对象|
|target_id|UUID|对象ID|
|recommendation|text|建议|
|priority|varchar|优先级|
|created_at|timestamp|时间|



---

# 4. 数据关系


关系：

stores

|

|

orders

|

|

order_items

|

|

products

|

|

sku_costs



库存：


products

|

inventory

费用：


stores

|

expenses




---

# 5. 利润计算流程


订单产生销售：


orders

↓

order_items

↓

匹配sku_costs

↓

计算产品成本

↓

计算毛利

↓

扣除费用

↓

生成profit_analysis



---

# 6. MVP阶段不包含


暂不设计：

- 多公司
- 多币种
- 财务凭证
- 自动采购
- 供应链预测
- 复杂权限系统


原因：

优先验证经营分析核心模型。


---

# 7. 后续扩展方向


V1.1:

增加：

广告数据表

采购数据表


V1.2:

增加：

预测模型

自动补货模型


V2.0:

增加：

多企业SaaS架构



---

# Version

V1.0

Date:

2026-08-01
