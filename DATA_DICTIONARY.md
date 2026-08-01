# DATA DICTIONARY

# 数据字典 V1.0


## 目标

建立统一数据标准。

所有 AI Agent、分析模型、Dashboard 必须使用统一字段。


---

# 一、商品主数据 Product Master


表：

products


|字段|说明|
|-|-|
|product_id|产品ID|
|sku|SKU编码|
|product_name|产品名称|
|category|分类|
|brand|品牌|
|supplier|供应商|
|lifecycle_status|生命周期|
|is_core_product|是否核心产品|
|seasonality|季节属性|


---

# 二、店铺数据 Store


表：

stores


|字段|说明|
|-|-|
|store_id|店铺ID|
|store_name|店铺名称|
|platform|平台|
|channel|渠道|
|store_type|店铺类型|


例如：

天猫旗舰店

京东店

抖音店


---

# 三、销售订单 Orders


表：

orders


|字段|说明|
|-|-|
|order_id|订单编号|
|order_date|订单日期|
|store_id|店铺|
|customer_id|客户|
|sku|产品|
|quantity|数量|
|sales_amount|销售金额|
|discount|折扣|
|sales_type|销售类型|


sales_type:

Retail

Wholesale

Promotion

Clearance

Sample


---

# 四、客户 Customer


表：

customers


字段：

customer_id

customer_name

customer_type


customer_type:


Normal Customer

Dealer

Distributor


---

# 五、成本数据 Cost


表：

sku_costs


核心原则：

同一个SKU允许不同店铺不同成本。


字段：

|字段|说明|
|-|-|
|sku|SKU|
|store_id|店铺|
|channel|渠道|
|cost_type|成本类型|
|unit_cost|单位成本|
|effective_date|生效日期|


---

# 六、费用数据 Expenses


表：

expenses


包括：

平台费用

广告费用

物流费用

赠品费用

运营费用


字段：

expense_type

amount

store_id

date


---

# 七、库存 Inventory


表：

inventory


字段：

sku

warehouse

available_qty

reserved_qty

inbound_qty

inventory_value


---

# 八、广告数据 Advertising


表：

advertising


字段：

store_id

campaign

date

spend

sales

roi


---

# 九、采购数据 Purchase


表：

purchase_orders


字段：

supplier

sku

purchase_qty

purchase_cost

delivery_date

lead_time


---

# 十、AI分析结果


表：

ai_insights


字段：

type

object_id

score

recommendation

created_at


例如：

库存风险

利润风险

采购建议
