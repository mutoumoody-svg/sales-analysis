# DEVELOPMENT STANDARD

# AI 企业经营决策平台开发规范 V1.0


## 1. 开发原则


所有开发必须遵循：

业务规则优先。

数据模型统一。

代码结构清晰。

结果可解释。



---

# 2. AI开发流程


任何 AI 开发前：

必须阅读：


1.

AI_CONTEXT.md


2.

BUSINESS_PHILOSOPHY.md


3.

BUSINESS_RULES.md


4.

DATA_DICTIONARY.md



然后开始编码。



---

# 3. 项目结构规范



推荐：

sales-analysis

├── README.md

├── AI_CONTEXT.md

├── docs/

├── backend/

├── frontend/

├── database/

├── api/

├── tests/

└── scripts/




---

# 4. 数据开发规范


禁止：

直接修改原始数据。


必须：

原始数据层

↓

清洗层

↓

业务层

↓

分析层



---

# 5. 数据库规范


要求：


所有表：

必须有主键。


所有业务数据：

必须记录时间。


所有计算结果：

必须保存来源。



---

# 6. API规范


接口必须：

清晰命名。

返回结构统一。


例如：


GET

/api/profit/store


返回：


store

revenue

cost

profit

margin



---

# 7. AI Agent开发规范


每个 Agent 必须定义：


职责

输入

处理逻辑

输出


禁止：

多个 Agent 重复负责同一任务。



---

# 8. 代码规范


要求：


代码可读。

变量命名清晰。

关键业务逻辑添加注释。



---

# 9. 版本管理


所有修改必须：

提交 Git。


Commit 信息说明：


例如：

add inventory health model

update cost matching rule




---

# 10. 业务规则修改


任何业务规则变化：

必须先修改：


docs/BUSINESS_RULES.md



然后修改代码。



禁止：

代码先改变业务逻辑。



---

# 11. 测试要求


每个核心模块必须测试：


销售计算

成本计算

利润计算

库存计算

现金流计算



---

# 12. 安全要求


企业数据：

默认私有。


禁止：

上传真实客户数据到公开仓库。



---

# 13. AI协作规范


未来任何 AI 接手项目：

必须：

先阅读文档。

理解业务。

确认数据结构。


然后开发。



---

# Version

V1.0

Date:

2026-08-01
