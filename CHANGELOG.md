# CHANGELOG

# AI Business Decision Platform


版本记录

---

# Unreleased

## 文档与配置整合

- 将 GitHub 备份中的 AI 上下文、版本记录和完整设计资料整合到本地代码主线
- 统一 Docker、后端和前端的环境变量样例
- 数据库与后端端口默认仅绑定本机，减少非预期暴露
- 部署脚本首次运行时要求先完成 `.env` 配置
- 前端 API 地址、开发端口和代理目标支持环境变量覆盖
- 后端数据库连接改为必填配置，避免使用代码内默认密码
- 修复前端 TypeScript/Ant Design 类型漂移并恢复完整生产构建
- 新增管理员 API Key，保护导入、同步和运营写操作
- 新增数据质量、成本维护与重算、采购确认、日报预警页面及 API
- 成本匹配支持店铺、渠道、标准、商品主数据与默认成本的分级回退
- 月度销售对比增加同比指标
- 销售预测增加异常月份识别与 95% 置信区间
- 新增数据库 `migrate_v4.sql` 和零依赖测试运行器



---

# V1.0

日期：

2026-08-01


## 初始版本建立


完成：


## 项目基础


- 创建 AI 企业经营决策平台定位
- 建立 GitHub 项目结构
- 建立 AI Knowledge Base


---

## 业务模型


新增：


- 销售分类模型

包括：

Retail

Wholesale

Promotion

Clearance

Sample



---

## 成本模型


新增：

多成本体系。


支持：


同 SKU

不同店铺

不同成本。


---

## 利润模型


建立：


销售收入

↓

产品成本

↓

毛利

↓

贡献利润

↓

净利润



---

## 库存模型


建立：


库存健康度

库存周转

安全库存

滞销分析



---

## 现金流模型


规划：

未来30/60/90天现金预测。



---

## AI Agent设计


建立：

Sales Agent

Inventory Agent

Procurement Agent

Finance Agent

Operation Agent

CEO Agent



---

## Dashboard设计


建立：

老板经营驾驶舱。


核心指标：

- 现金健康度
- 库存健康度
- 利润健康度


---

# Future Version


## V1.1


计划：


- ERP数据接口
- 旺店通连接
- 数据导入模块
- 自动利润计算


---

## V1.2


计划：


- AI销售预测
- 自动补货建议
- 广告优化模型


---

## V2.0


计划：


- 多企业支持
- SaaS化
- 自动经营决策
