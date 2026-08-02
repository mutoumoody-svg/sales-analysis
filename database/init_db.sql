-- ============================================
-- AI Business Decision Platform
-- Database Initialization Script
-- ============================================
--
-- Usage:
--   psql -U postgres -d sales_analysis -f init_db.sql
--
-- Or create database first:
--   CREATE DATABASE sales_analysis;
--   \c sales_analysis
--   \i init_db.sql
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. stores - 店铺表
-- ============================================
CREATE TABLE IF NOT EXISTS stores (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_name  VARCHAR(200) NOT NULL,
    platform    VARCHAR(50)  NOT NULL,
    channel     VARCHAR(50),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stores_name ON stores(store_name);

-- ============================================
-- 2. products - 商品主表
-- ============================================
CREATE TABLE IF NOT EXISTS products (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku           VARCHAR(100) NOT NULL UNIQUE,
    product_name  VARCHAR(300) NOT NULL,
    category      VARCHAR(100),
    brand         VARCHAR(100),
    supplier      VARCHAR(200),
    status        VARCHAR(20)  NOT NULL DEFAULT 'active',
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- ============================================
-- 3. customers - 客户表
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_name  VARCHAR(200),
    customer_type  VARCHAR(30) NOT NULL DEFAULT 'Normal',
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_type ON customers(customer_type);

-- ============================================
-- 4. orders - 订单主表
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_no      VARCHAR(100) NOT NULL UNIQUE,
    order_date    DATE NOT NULL,
    store_id      UUID NOT NULL REFERENCES stores(id),
    customer_id   UUID REFERENCES customers(id),
    sales_type    VARCHAR(20) NOT NULL DEFAULT 'Retail',
    total_amount  NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_store ON orders(store_id);
CREATE INDEX IF NOT EXISTS idx_orders_sales_type ON orders(sales_type);

-- ============================================
-- 5. order_items - 订单明细表
-- ============================================
CREATE TABLE IF NOT EXISTS order_items (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id      UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id    UUID NOT NULL REFERENCES products(id),
    quantity      INTEGER NOT NULL DEFAULT 1,
    selling_price NUMERIC(14,2) NOT NULL,
    amount        NUMERIC(14,2) NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);

-- ============================================
-- 6. sku_costs - SKU成本表 (核心表)
--    支持同SKU不同店铺不同成本
-- ============================================
CREATE TABLE IF NOT EXISTS sku_costs (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id     UUID NOT NULL REFERENCES products(id),
    store_id       UUID REFERENCES stores(id),
    cost_type      VARCHAR(30) NOT NULL DEFAULT 'standard',
    unit_cost      NUMERIC(14,4) NOT NULL,
    effective_date DATE NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sku_costs_product ON sku_costs(product_id);
CREATE INDEX IF NOT EXISTS idx_sku_costs_store ON sku_costs(store_id);
CREATE INDEX IF NOT EXISTS idx_sku_costs_effective ON sku_costs(effective_date);

-- ============================================
-- 7. inventory - 库存表
-- ============================================
CREATE TABLE IF NOT EXISTS inventory (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id    UUID NOT NULL REFERENCES products(id),
    warehouse     VARCHAR(100) NOT NULL DEFAULT 'default',
    available_qty INTEGER NOT NULL DEFAULT 0,
    reserved_qty  INTEGER NOT NULL DEFAULT 0,
    inbound_qty   INTEGER NOT NULL DEFAULT 0,
    date          DATE NOT NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_date ON inventory(date);

-- ============================================
-- 8. expenses - 费用表
-- ============================================
CREATE TABLE IF NOT EXISTS expenses (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id     UUID NOT NULL REFERENCES stores(id),
    expense_type VARCHAR(30) NOT NULL,
    amount       NUMERIC(14,2) NOT NULL,
    date         DATE NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_store ON expenses(store_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_type ON expenses(expense_type);

-- ============================================
-- 9. profit_analysis - 利润分析结果表
-- ============================================
CREATE TABLE IF NOT EXISTS profit_analysis (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date                DATE NOT NULL,
    store_id            UUID NOT NULL REFERENCES stores(id),
    product_id          UUID NOT NULL REFERENCES products(id),
    revenue             NUMERIC(14,2) NOT NULL DEFAULT 0,
    cost                NUMERIC(14,2) NOT NULL DEFAULT 0,
    gross_profit        NUMERIC(14,2) NOT NULL DEFAULT 0,
    contribution_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_profit          NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profit_date ON profit_analysis(date);
CREATE INDEX IF NOT EXISTS idx_profit_store ON profit_analysis(store_id);
CREATE INDEX IF NOT EXISTS idx_profit_product ON profit_analysis(product_id);

-- ============================================
-- 10. ai_recommendations - AI建议表
-- ============================================
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type      VARCHAR(50) NOT NULL,
    target_type     VARCHAR(50),
    target_id       UUID,
    recommendation  TEXT NOT NULL,
    priority        VARCHAR(20) NOT NULL DEFAULT 'Medium',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_agent ON ai_recommendations(agent_type);
CREATE INDEX IF NOT EXISTS idx_ai_priority ON ai_recommendations(priority);

-- ============================================
-- Done
-- ============================================
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully. 10 tables created.';
END $$;
