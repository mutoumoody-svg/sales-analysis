// ===== Types =====

export interface OverviewData {
  total_revenue: number;        // 实际销售额（扣除退货）
  total_ship_amount: number;     // 发货总金额
  return_amount: number;         // 退货总金额
  return_rate: number;           // 退货率 %
  order_count: number;
  gross_profit: number;          // 实际利润（扣除退货后）
  gross_margin_pct: number;
  total_cost: number;            // 实际成本（按实际发货量）
  commission_cost: number;       // 佣金成本
  total_discount: number;
  store_count: number;
  product_count: number;
  date_range: { start: string | null; end: string | null };
}

export interface StoreSales {
  store_id: string;
  store_name: string;
  platform: string;
  channel: string | null;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  total_revenue: number;       // 实际销售额（扣除退货）
  total_cost: number;          // 实际成本
  gross_profit: number;        // 实际利润
  gross_margin_pct: number;
  commission_cost: number;
}

export interface ProductSales {
  product_id: string;
  sku: string;
  product_name: string;
  category: string | null;
  ship_qty: number;
  return_qty: number;
  total_qty: number;           // 实际销售量（扣除退货）
  total_revenue: number;       // 实际销售额
  total_cost: number;          // 实际成本（按实际发货量）
  gross_profit: number;
  gross_margin_pct: number;
}

export interface DailyTrendItem {
  date: string;
  order_count: number;
  revenue: number;
  gross_profit: number;
  gross_margin_pct: number;
  discount: number;
}

export interface PlatformSales {
  platform: string;
  store_count: number;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  total_revenue: number;
  total_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
}

export interface CategorySales {
  category: string;
  sku_count: number;
  total_qty: number;
  total_revenue: number;
  total_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
}

export interface ProfitSummary {
  order_count: number;
  revenue: number;
  gross_profit: number;
  gross_margin_pct: number;
  shipping_fee: number;
  shipping_cost: number;
  packaging_cost: number;
  discount: number;
  contribution_profit: number;
  net_profit: number;
  net_margin_pct: number;
}

export interface StoreProfit {
  store_id: string;
  store_name: string;
  platform: string;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  order_count: number;
  revenue: number;
  net_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
  commission_cost: number;
  shipping_cost: number;
  packaging_cost: number;
  contribution_profit: number;
  net_profit: number;
}

export interface ProductProfit {
  product_id: string;
  sku: string;
  product_name: string;
  category: string | null;
  store_name: string;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  net_revenue: number;
  net_cost: number;
  ship_profit: number;
  net_profit: number;
  net_margin_pct: number;
}

export interface LowMarginItem {
  sku: string;
  product_name: string;
  category: string | null;
  store_name: string;
  net_qty: number;
  net_revenue: number;
  net_cost: number;
  net_profit: number;
  net_margin_pct: number;
  risk_level: 'loss' | 'low_margin';
}

export interface InventoryItem {
  sku: string;
  product_name: string;
  brand: string | null;
  warehouse: string;
  available_qty: number;
  reserved_qty: number;
  inbound_qty: number;
  effective_qty: number;
  risk_level: 'stockout' | 'low_stock' | 'overstock' | 'healthy';
}

export interface InventoryHealth {
  health_score: number;
  total_skus: number;
  stockout_count: number;
  low_stock_count: number;
  overstock_count: number;
  items: InventoryItem[];
}

export interface InventoryAnalysisItem {
  sku: string;
  product_name: string;
  brand: string | null;
  warehouse: string;
  available_qty: number;
  reserved_qty: number;
  inbound_qty: number;
  effective_qty: number;
  unit_cost: number;
  capital_occupied: number;
  total_sold_qty: number;
  daily_rate: number;
  turnover_days: number | null;
  last_sale_date: string | null;
  stale_days: number | null;
  is_stale: boolean;
  safety_stock: number;
  reorder_qty: number;
  needs_reorder: boolean;
  status: 'stockout' | 'stale' | 'reorder' | 'overstock' | 'healthy';
}

export interface InventoryAnalysisSummary {
  total_capital: number;
  avg_turnover_days: number;
  stale_count: number;
  reorder_count: number;
  total_skus: number;
  stockout_count: number;
  overstock_count: number;
  healthy_count: number;
  date_span: number;
  data_start: string;
  data_end: string;
}

export interface InventoryAnalysis {
  summary: InventoryAnalysisSummary;
  items: InventoryAnalysisItem[];
}

export interface HealthIndex {
  overall_score: number;
  grade: string;
  sales_health: number;
  inventory_health: number;
  profit_health: number;
  metrics: {
    net_revenue: number;
    net_profit: number;
    gross_margin: number;
    return_rate: number;
    total_inv_skus: number;
    stockout_count: number;
    low_stock_count: number;
  };
}

export interface CeoReportItem {
  title: string;
  detail: string;
  priority: 'high' | 'medium' | 'low';
}

export interface CeoReport {
  summary: {
    revenue: number;
    profit: number;
    gross_margin: number;
    return_rate: number;
    ship_qty: number;
    return_qty: number;
    sku_count: number;
    stockout_count: number;
  };
  opportunities: CeoReportItem[];
  risks: CeoReportItem[];
  actions: string[];
}

export interface StoreOption {
  id: string;
  store_name: string;
  platform: string;
  channel: string | null;
}

export interface CategoryOption {
  category: string;
  product_count: number;
}
