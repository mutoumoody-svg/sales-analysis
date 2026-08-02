-- Migration v3: sales_summary 增加 period 字段，支持按月分析
-- 执行方式: psql -U postgres -d sales_analysis -f migrate_v3.sql

-- 1. 加 period 列（默认值 2026-07，对应当前已有数据）
ALTER TABLE sales_summary ADD COLUMN IF NOT EXISTS period VARCHAR(7) NOT NULL DEFAULT '2026-07';

-- 2. 加索引
CREATE INDEX IF NOT EXISTS idx_sales_summary_period ON sales_summary(period);

-- 3. 删旧唯一约束
ALTER TABLE sales_summary DROP CONSTRAINT IF EXISTS uq_sales_summary_store_product;

-- 4. 加新唯一约束（store_id + product_id + period）
ALTER TABLE sales_summary ADD CONSTRAINT uq_sales_summary_store_product_period
    UNIQUE (store_id, product_id, period);

-- 5. 确认结果
SELECT period, count(*) FROM sales_summary GROUP BY period ORDER BY period;
