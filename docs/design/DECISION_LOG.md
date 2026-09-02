# DECISION LOG

# AI 企业经营决策平台设计决策记录 V1.0


## 目的

记录项目重要设计决策。

避免未来开发过程中：

- 忘记设计原因
- AI错误修改核心逻辑
- 不同开发人员理解不一致


---

# Decision 001

## 项目定位

日期：

2026-08-01


决定：

本项目定位为：

AI 企业经营决策平台。


不是：

传统 ERP。


原因：

ERP 主要负责记录业务。

企业真正需要的是：

理解数据并辅助决策。


---

# Decision 002

## 使用业务规则优先


决定：

第一阶段采用：

Business Rules + AI


而不是：

完全自主AI。


原因：

企业经营规则需要稳定和可解释。


AI负责：

分析

预测

优化


业务规则负责：

定义标准。


---

# Decision 003

## 同 SKU 支持不同店铺成本


决定：

同一个 SKU 可以存在多个成本。


例如：


SKU001


天猫成本：

18元


京东成本：

20元


抖音成本：

22元



原因：

不同渠道：

采购价格

物流成本

运营方式

可能不同。


如果使用统一成本：

利润分析会失真。



---

# Decision 004

## 销售分类独立设计


决定：

销售必须区分：


Retail

Wholesale

Promotion

Clearance

Sample



原因：

批发订单会影响：

销量预测

库存预测

经营分析。


不能和普通零售混合。


---

# Decision 005

## 不以最高毛利率为目标


决定：

系统寻找：

最佳经营区间。


不是：

最高毛利率。


原因：

企业经营是平衡：

销售增长

利润

库存

现金流


高毛利不一定代表高利润。


---

# Decision 006

## 现金流作为核心指标


决定：

现金健康度作为老板驾驶舱核心指标之一。


原因：

企业失败很多时候不是亏损。

而是：

现金无法支撑经营。



---

# Decision 007

## AI Agent 分工设计


决定：

采用多个专业 Agent。


包括：

Sales Agent

Inventory Agent

Finance Agent

Procurement Agent

CEO Agent



原因：

复杂经营问题需要专业分工。


---

# Decision 008

## 数据和分析分离


决定：

原始数据不可直接修改。


采用：


Raw Data

↓

Clean Data

↓

Business Data

↓

Analysis Data



原因：

保证数据追溯。



---

# Decision 009

## Dashboard 面向老板


决定：

首页设计为：

经营驾驶舱。


不是传统报表。


原因：

老板关注：

问题

风险

行动。


不是大量数据。


---

# Decision 010

## AI开发必须先读文档


决定：

所有 AI 开发：

必须先阅读：


AI_CONTEXT.md

BUSINESS_RULES.md

DATA_DICTIONARY.md



原因：

保证开发一致性。


---

# Future Decisions


以后新的重大设计：

必须增加新的 Decision 编号。


格式：


Decision XXX

日期

决定

原因

影响
