-- Configurable per-SKU ordering policies.

CREATE TABLE IF NOT EXISTS reorder_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL UNIQUE REFERENCES products(id) ON DELETE CASCADE,
    lead_time_days INTEGER NOT NULL DEFAULT 60 CHECK (lead_time_days BETWEEN 1 AND 365),
    review_period_days INTEGER NOT NULL DEFAULT 30 CHECK (review_period_days BETWEEN 0 AND 180),
    safety_days INTEGER CHECK (safety_days BETWEEN 0 AND 180),
    min_order_qty INTEGER NOT NULL DEFAULT 1 CHECK (min_order_qty >= 1),
    order_multiple INTEGER NOT NULL DEFAULT 1 CHECK (order_multiple >= 1),
    max_stock_days INTEGER NOT NULL DEFAULT 180 CHECK (max_stock_days BETWEEN 1 AND 730),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_reorder_policies_product_id ON reorder_policies(product_id);
