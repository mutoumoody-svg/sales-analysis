# DATABASE DESIGN

# 数据库设计 V1.0


## 数据库目标


支持：

销售分析

库存分析

利润分析

AI Agent


---

# 核心数据表


## products

商品表


```sql
products

id

sku

name

category

brand

supplier

status

stores

店铺表

stores

id

name

platform

channel

orders

销售订单

orders

id

order_date

store_id

customer_id

sales_type

total_amount

order_items

订单明细

order_items

order_id

sku

quantity

price

cost


sku_costs

成本表

支持：

同SKU不同店铺成本

sku_costs

id

sku

store_id

cost_type

unit_cost

effective_date

inventory

库存表

inventory

sku

warehouse

available_qty

reserved_qty

inbound_qty

expenses

费用表

expenses

id

store_id

type

amount

date

advertising

广告表


advertising

id

store_id

campaign

spend

sales

roi

profit_analysis

利润分析结果

profit_analysis

date

store_id

sku

revenue

cost

gross_profit

contribution_profit

net_profit

ai_recommendations

AI建议

ai_recommendations

id

agent_type

target

recommendation

priority

数据关系

Store

 |

Orders

 |

Order Items

 |

SKU

 |

Cost

数据原则

原始数据不可修改。

分析数据单独生成。

所有计算必须可追溯。

AI建议必须保存来源数据。


---

这两份完成后，下一批继续：

1. `SYSTEM_ARCHITECTURE.md`
2. `AGENT_DESIGN.md`

这两个文件会定义**程序怎么写、Agent怎么协同**，是交给 AI 开发最重要的部分。