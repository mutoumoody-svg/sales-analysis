-- Operational hardening: channel costs and confirmable purchase plans.

ALTER TABLE sku_costs ADD COLUMN IF NOT EXISTS channel VARCHAR(50);
CREATE INDEX IF NOT EXISTS ix_sku_costs_channel ON sku_costs(channel);

CREATE TABLE IF NOT EXISTS purchase_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id),
    store_id UUID REFERENCES stores(id),
    period VARCHAR(7) NOT NULL,
    suggested_qty INTEGER NOT NULL,
    confirmed_qty INTEGER,
    unit_cost NUMERIC(14,4),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    source VARCHAR(50) NOT NULL DEFAULT 'reorder_engine',
    notes TEXT,
    confirmed_by VARCHAR(100),
    confirmed_at TIMESTAMP,
    expected_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_purchase_plans_period ON purchase_plans(period);
CREATE INDEX IF NOT EXISTS ix_purchase_plans_status ON purchase_plans(status);
