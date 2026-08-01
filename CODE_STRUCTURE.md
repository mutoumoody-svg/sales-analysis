# CODE STRUCTURE

# AI 企业经营决策平台代码结构规范 V1.0


## 项目目录


sales-analysis/


├── backend/

│
├── frontend/

│
├── database/

│
├── docs/

│
├── tests/

│
├── scripts/

│
├── docker/

│
├── README.md

└── AI_CONTEXT.md



---

# backend 后端


负责：

业务逻辑

API

数据处理

AI Agent


结构：


backend/


├── app/

│
├── api/

│
├── models/

│
├── services/

│
├── agents/

│
├── utils/

│
└── tests/



---

# frontend 前端


负责：

Dashboard展示。


结构：


frontend/


├── src/

│
├── components/

│
├── pages/

│
├── charts/

│
└── services/



---

# database


负责：

数据库结构。


包括：


schema

migration

seed data



---

# tests


负责：

自动化测试。


包括：


业务规则测试

利润测试

API测试



---

# scripts


负责：

数据处理脚本。


例如：


Excel导入

数据清洗



---

# 开发原则


业务逻辑：

backend/services


数据模型：

backend/models


AI能力：

backend/agents


页面：

frontend/pages



禁止：

所有代码写在一个文件。
