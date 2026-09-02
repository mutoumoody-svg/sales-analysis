# AI Business Decision Platform

## AI 企业经营决策平台 V1.0


## 项目定位

本项目不是传统 ERP 系统。

ERP 的作用：

记录企业发生了什么。


本系统的目标：

利用 ERP、电商、财务、库存、广告等数据，通过 AI 分析帮助企业进行经营决策。


系统回答的问题：

- 哪些产品真正赚钱？
- 哪些库存正在占用现金？
- 哪些店铺需要优化？
- 广告投入是否值得？
- 应该采购多少库存？
- 如何提高资金利用效率？
- 如何找到最佳经营区间？


---

# 核心理念

企业经营本质：

现金

↓

采购

↓

库存

↓

销售

↓

利润

↓

现金回流


系统目标：

提高：

- 现金周转效率
- 库存效率
- 利润质量
- 决策效率


---

# 核心功能

## 1. 数据中心

支持：

- 旺店通 ERP
- 电商平台
- Excel
- CSV
- 数据库接口


---

## 2. 销售分析

支持：

- 店铺分析
- SKU分析
- 客户分析
- 渠道分析
- 销售趋势


---

## 3. 利润分析

支持：

- 毛利分析
- 贡献利润分析
- 净利润分析
- 利润健康评分


---

## 4. 库存分析

支持：

- 库存健康度
- 周转分析
- 滞销分析
- 安全库存
- 补货建议


---

## 5. AI Agent

包括：

Sales Agent

Inventory Agent

Procurement Agent

Finance Agent

Operation Agent

CEO Agent


---

# 开发原则


业务规则优先。

所有 AI 分析必须建立在明确业务规则基础上。


开发顺序：

需求确认

↓

业务规则

↓

数据模型

↓

代码开发

↓

测试

↓

上线


---

# Version

V1.0

Date:

2026-08-01

---

# 当前实现

项目现已包含可运行的 FastAPI 后端、React/Vite 前端、PostgreSQL 数据库结构和 Docker Compose 部署配置。当前代码主线位于本仓库根目录，原始设计资料收录在 `docs/design/`。

当前还包含“运营设置”模块：数据质量评分、多层级成本维护、历史成本重算、采购草案确认和 Agent 日报预警。销售分析支持环比与同比，预测模块支持异常月份识别和 95% 预测区间。

继续开发前请依次阅读：

1. `AI_CONTEXT.md`
2. `docs/CONFIGURATION.md`
3. `docs/MIGRATION.md`
4. 与本次功能相关的 `docs/design/` 文档

# 本地开发

后端：

```bash
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Docker：

```bash
copy .env.example .env
# 修改 .env，至少设置 DB_PASSWORD 和生产环境 CORS_ORIGINS
docker compose up -d --build
```

已有数据库升级：

```bash
docker compose exec -T db psql -U postgres -d sales_analysis < database/migrate_v4.sql
```

测试：

```bash
backend\.venv\Scripts\python.exe scripts\run_tests.py
cd frontend && npm run lint && npm run build
```
