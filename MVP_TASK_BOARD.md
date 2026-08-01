# MVP TASK BOARD

# AI 企业经营决策平台 MVP 开发任务清单 V1.0


## 项目目标


完成第一版可运行系统。


实现：

输入：

销售数据


输出：

销售分析

利润分析

库存分析

AI经营建议



---

# 开发原则


按照：

基础设施

↓

数据层

↓

业务逻辑

↓

分析模型

↓

展示层

↓

AI能力


顺序开发。



---

# Phase 0 项目初始化


## TASK-001

建立项目代码结构


状态：

TODO


内容：


创建：


backend/

frontend/

database/

tests/


验收：

项目可以正常运行。



---

## TASK-002

建立开发环境


状态：

TODO


内容：


配置：

Python环境

Node环境

PostgreSQL


验收：

开发环境启动成功。



---

# Phase 1 数据库开发


## TASK-101

创建数据库


状态：

TODO


内容：


建立：

PostgreSQL数据库



---

## TASK-102

创建基础数据表


状态：

TODO


创建：


stores


products


customers


orders


order_items


sku_costs


inventory


expenses



验收：

数据库结构符合：

MVP_DATABASE_SCHEMA.md



---

## TASK-103

建立数据关系


状态：

TODO


内容：


设置：

主键

外键

索引



---

# Phase 2 数据导入模块


## TASK-201

Excel导入功能


状态：

TODO


支持：

orders.xlsx

products.xlsx

inventory.xlsx



验收：

文件可以上传。


---

## TASK-202

数据字段映射


状态：

TODO


实现：

Excel字段

↓

数据库字段



---

## TASK-203

数据质量检查


状态：

TODO


检查：

SKU缺失

日期错误

成本缺失


输出：

错误报告。



---

# Phase 3 业务规则开发


## TASK-301

销售类型分类


状态：

TODO


实现：


Retail

Wholesale

Promotion

Clearance

Sample



---

## TASK-302

批发订单识别


状态：

TODO


规则：

经销商客户

大数量订单



---

## TASK-303

成本匹配引擎


状态：

TODO


实现：


优先级：


1.

店铺成本


2.

渠道成本


3.

标准成本



验收：

同SKU不同店铺成本正确计算。



---

# Phase 4 利润计算


## TASK-401

毛利计算


状态：

TODO


公式：


销售收入

-

产品成本


=

毛利



---

## TASK-402

贡献利润计算


状态：

TODO


扣除：


广告费用

平台费用

物流费用

赠品成本



---

## TASK-403

净利润计算


状态：

TODO


输出：

真实利润。



---

# Phase 5 分析模型


## TASK-501

店铺利润分析


状态：

TODO


输出：


店铺销售

毛利

净利润

利润率



---

## TASK-502

SKU利润分析


状态：

TODO


输出：


SKU销售

成本

利润贡献



---

## TASK-503

库存健康分析


状态：

TODO


输出：


库存评分

滞销商品

风险库存



---

# Phase 6 Dashboard


## TASK-601

建立首页Dashboard


状态：

TODO


显示：


现金健康度

库存健康度

利润健康度



---

## TASK-602

利润分析页面


状态：

TODO


显示：

利润瀑布图

店铺利润

SKU利润



---

## TASK-603

库存分析页面


状态：

TODO


显示：

库存金额

周转率

风险列表



---

# Phase 7 AI Agent


## TASK-701

Sales Agent


状态：

TODO


功能：

销售趋势分析。



---

## TASK-702

Finance Agent


状态：

TODO


功能：

利润和现金分析。



---

## TASK-703

Inventory Agent


状态：

TODO


功能：

库存建议。



---

## TASK-704

CEO Agent


状态：

TODO


功能：

生成老板日报。



---

# Phase 8 测试


## TASK-801

数据准确性测试


检查：


销售金额

成本

利润



---

## TASK-802

业务规则测试


检查：


批发分类

成本匹配

利润计算



---

## TASK-803

性能测试


检查：

数据量

查询速度



---

# MVP完成标准


满足以下条件：


## 数据输入


可以导入：

一个月销售数据。



---

## 数据处理


自动完成：

SKU识别

店铺识别

成本匹配

利润计算



---

## 输出结果


生成：


店铺利润排名


SKU利润排名


库存风险


AI经营建议



---

# 后续版本


## V1.1


增加：

旺店通API

广告数据

采购数据



---

## V1.2


增加：

销售预测

自动补货

广告优化



---

## V2.0


增加：

企业级AI经营系统



---

# Version

V1.0

Date:

2026-08-01
