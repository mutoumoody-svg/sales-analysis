-- Confirmed monthly accounting results synchronized from sales.riverline.com.cn.

CREATE TABLE IF NOT EXISTS monthly_accounting_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    period VARCHAR(7) NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL DEFAULT 'sales_agent',
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    store_count INTEGER NOT NULL DEFAULT 0,
    revenue NUMERIC(16,2) NOT NULL DEFAULT 0,
    cost NUMERIC(16,2) NOT NULL DEFAULT 0,
    gross_profit NUMERIC(16,2) NOT NULL DEFAULT 0,
    operating_profit NUMERIC(16,2) NOT NULL DEFAULT 0,
    synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monthly_accounting_stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID NOT NULL REFERENCES monthly_accounting_batches(id) ON DELETE CASCADE,
    store_name VARCHAR(200) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    source_key VARCHAR(250),
    revenue NUMERIC(16,2) NOT NULL DEFAULT 0,
    cost NUMERIC(16,2) NOT NULL DEFAULT 0,
    gross_profit NUMERIC(16,2) NOT NULL DEFAULT 0,
    ad_fee NUMERIC(16,2) NOT NULL DEFAULT 0,
    platform_fee NUMERIC(16,2) NOT NULL DEFAULT 0,
    tax_fee NUMERIC(16,2) NOT NULL DEFAULT 0,
    logistics_fee NUMERIC(16,2) NOT NULL DEFAULT 0,
    operating_profit NUMERIC(16,2) NOT NULL DEFAULT 0,
    order_count INTEGER NOT NULL DEFAULT 0,
    sales_qty INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_monthly_accounting_store UNIQUE(batch_id, store_name, platform)
);

CREATE INDEX IF NOT EXISTS ix_monthly_accounting_batches_period ON monthly_accounting_batches(period);
CREATE INDEX IF NOT EXISTS ix_monthly_accounting_stores_batch ON monthly_accounting_stores(batch_id);
