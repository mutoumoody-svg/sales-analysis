-- ============================================
-- 迁移脚本: 适配新旺店通数据结构
-- 1. orders 表新增成本/毛利字段
-- 2. order_items 表新增成本/仓库字段
-- 3. 新增 sales_summary 表
-- ============================================

-- 1. orders 表新增字段
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_fee NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_cost NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS packaging_cost NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gross_profit NUMERIC(14,2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS gross_profit_rate NUMERIC(8,4);

COMMENT ON COLUMN orders.discount IS '订单总优惠';
COMMENT ON COLUMN orders.shipping_fee IS '邮费';
COMMENT ON COLUMN orders.shipping_cost IS '邮资成本';
COMMENT ON COLUMN orders.packaging_cost IS '订单包装成本';
COMMENT ON COLUMN orders.gross_profit IS '订单毛利';
COMMENT ON COLUMN orders.gross_profit_rate IS '毛利率';

-- 2. order_items 表新增字段
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(14,4);
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS total_cost NUMERIC(14,2);
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS warehouse VARCHAR(100);

COMMENT ON COLUMN order_items.unit_cost IS '货品成本(单价)';
COMMENT ON COLUMN order_items.total_cost IS '货品总成本';
COMMENT ON COLUMN order_items.warehouse IS '仓库';

-- 3. 新增 sales_summary 表
CREATE TABLE IF NOT EXISTS sales_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    product_id UUID NOT NULL REFERENCES products(id),

    -- 数量
    ship_qty INTEGER NOT NULL DEFAULT 0,
    return_qty INTEGER NOT NULL DEFAULT 0,
    net_qty INTEGER NOT NULL DEFAULT 0,
    unshipped_refund_qty INTEGER NOT NULL DEFAULT 0,
    gift_qty INTEGER NOT NULL DEFAULT 0,

    -- 金额
    avg_price NUMERIC(14,4),
    ship_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    return_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    unshipped_refund_amount NUMERIC(14,2) NOT NULL DEFAULT 0,

    -- 成本
    total_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
    return_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
    commission_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
    unknown_cost_sales NUMERIC(14,2) NOT NULL DEFAULT 0,

    -- 利润
    ship_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_profit NUMERIC(14,2) NOT NULL DEFAULT 0,

    CONSTRAINT uq_sales_summary_store_product UNIQUE (store_id, product_id),

    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sales_summary_store ON sales_summary(store_id);
CREATE INDEX IF NOT EXISTS idx_sales_summary_product ON sales_summary(product_id);

DO $$ BEGIN RAISE NOTICE 'Migration completed: orders + order_items + sales_summary'; END $$;
