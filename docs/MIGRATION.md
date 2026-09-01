# 系统迁移指南

代码仓库：https://github.com/mutoumoody-svg/sales-analysis（main = 最新）

## 代码之外的服务器资产（不在 git 里，迁移时需单独处理）

生产服务器：`122.51.255.195`（腾讯云 Ubuntu，SSH 用户 ubuntu）

| 组件 | 位置 | 说明 |
|---|---|---|
| 后端运行目录 | `/home/ubuntu/sales-analysis` | venv + 源码，systemd 服务 `sales-analysis`（FastAPI :8000） |
| 前端静态文件 | `/var/www/sales-analysis/dist` | Vite 构建产物，nginx 托管，域名 `fenxi.riverline.com.cn` |
| 数据库 | PostgreSQL 16，库名 `sales_analysis` | 表：products / orders / order_items / sales_summary / stores / sku_costs |
| 出库数据源 | `/opt/kucun` | 独立系统，抓旺店通出库明细到 `/opt/kucun/output/daily_outbound/日期.json`，实时销售页读这里 |
| 订单/退款输出 | `/opt/sales-analysis/output/` | trade_daily / refund_daily 目录，店铺日报页读这里 |
| 定时任务 | `crontab -l` | 详见下表 |

## 定时任务一览（crontab）

| 时间 | 任务 | 脚本 |
|---|---|---|
| 01:30 | 拉前一天三品牌订单 + 近30天退款 | `cron_fetch_trade.sh` |
| 8:10~23:10 每小时 | 抓当天出库 + 订单 + 退款（准实时） | `cron_fetch_today.sh` |
| 22:00 | kucun 每日同步（昨天出库明细 + 当月汇总 + 库存） | `/opt/kucun/scripts/daily_sync.sh` |
| 01:00 | 旺店通库存同步到数据库 | `curl POST /api/v1/inventory/sync-from-wangdian` |

## 环境变量（脱敏后必须配置）

```bash
# backend/.env
DATABASE_URL=postgresql://postgres:<密码>@localhost:5432/sales_analysis

# 旺店通API凭证（fetch脚本用，不要写进代码）
WANGDIAN_SID=...
WANGDIAN_APPKEY=...
WANGDIAN_APPSECRET=...
```

## 前端构建（Windows 注意）

Windows 上 Vite 8 无法加载 .ts 配置，用程序化构建：

```bash
cd frontend && node build.cjs   # 输出 dist/，emptyOutDir: false
```

部署：`dist/` 上传到 `/var/www/sales-analysis/dist/`（属主 www-data，需 sudo）。
注意 PWA service worker 有缓存，更新后需硬刷新验证。

## 数据迁移

```bash
# 服务器上导出
pg_dump sales_analysis > sales_analysis_backup.sql
```

`products.unit_cost` 是全系统唯一成本来源（旺店通 cost_price 不参与利润计算），迁移数据库时必须带上。
