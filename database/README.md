# Database Scripts

This directory contains database initialization and migration scripts.

## Files

| File | Description |
|------|-------------|
| `init_db.sql` | PostgreSQL initialization script (creates all 10 tables) |

## Quick Start

### Option 1: SQL Script (recommended for production)

```bash
# Create database
psql -U postgres -c "CREATE DATABASE sales_analysis;"

# Run init script
psql -U postgres -d sales_analysis -f database/init_db.sql
```

### Option 2: SQLAlchemy Auto-create (for development)

```bash
cd backend
python -m app.create_tables
```

## Tables Overview

| # | Table | Purpose |
|---|-------|---------|
| 1 | stores | 店铺表 |
| 2 | products | 商品主表 (SKU) |
| 3 | customers | 客户表 |
| 4 | orders | 订单主表 |
| 5 | order_items | 订单明细表 |
| 6 | sku_costs | SKU成本表 (核心：同SKU不同店铺不同成本) |
| 7 | inventory | 库存表 |
| 8 | expenses | 费用表 |
| 9 | profit_analysis | 利润分析结果表 |
| 10 | ai_recommendations | AI建议表 |
