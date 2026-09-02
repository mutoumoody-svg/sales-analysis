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
  order_count: number;
  total_discount: number;
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
  order_count: number;
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
  net_cost: number;
  commission_cost: number;
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

export interface MonthlySalesData {
  period: string;
  qty: number;
  daily_rate: number;
  weight: number;
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
  // 新增：多月加权补货字段
  monthly_sales: MonthlySalesData[];
  weighted_daily_rate: number;
  trend_pct: number;
  trend_direction: 'up' | 'down' | 'stable';
  turnover_category: 'fast' | 'slow';
  safety_factor: number;
  cycle_demand: number;
  reorder_value: number;
  priority: 'urgent' | 'normal' | 'planned' | 'none';
  days_of_supply: number | null;
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
  // 新增：补货引擎字段
  urgent_count: number;
  normal_count: number;
  planned_count: number;
  total_reorder_qty: number;
  total_reorder_value: number;
  fast_moving_count: number;
  slow_moving_count: number;
  periods: string[];
  procurement_days: number;
  weighted_months: number;
  month_weights: number[];
  safety_factor_fast: number;
  safety_factor_slow: number;
  turnover_threshold_days: number;
  period?: string;
  data_start?: string;
  data_end?: string;
}

export interface InventoryAnalysis {
  summary: InventoryAnalysisSummary;
  items: InventoryAnalysisItem[];
}

// ===== Kucun 同步状态 =====
export interface KucunSyncResult {
  status: 'success' | 'error' | 'no_change';
  message: string;
  synced_date: string | null;
  inserted: number;
  updated: number;
  unchanged: number;
  matched_count: number;
  auto_created: number;
  auto_created_skus: Array<{ sku: string; name: string }>;
  total_kucun_items: number;
  unmatched_count: number;
  unmatched_skus: Array<{ sku: string; name: string }>;
  last_sync_at: string | null;
}

// ===== 旺店通 API 同步状态 =====

export interface WangdianSyncStatus {
  configured: boolean;
  within_allowed_time: boolean;
  allowed_time_window: string;
  last_sync_at: string | null;
  last_synced_date: string | null;
  last_total_from_api: number | null;
  last_matched: number | null;
  last_auto_created: number | null;
  last_inserted: number | null;
  last_updated: number | null;
  last_warehouses: string[];
  last_warehouse_count: number;
  sales_analysis_latest_date: string | null;
  data_source: string;
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

// ===== AI Agent =====

export interface AgentRecommendation {
  recommendation: string;
  priority: 'High' | 'Medium' | 'Low';
  target_type?: string;
  target_id?: string;
}

export interface SalesAgentResult {
  agent_type: string;
  summary: {
    revenue: number;
    profit: number;
    cost: number;
    gross_margin: number;
    ship_qty: number;
    return_qty: number;
    net_qty: number;
    return_rate: number;
    commission: number;
  };
  mom?: {
    prev_period: string;
    prev_revenue: number;
    prev_profit: number;
    revenue_change_pct: number;
    profit_change_pct: number | null;
  };
  stores: Array<{
    store_name: string;
    platform: string;
    revenue: number;
    profit: number;
    ship_qty: number;
    return_rate: number;
  }>;
  top_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    qty: number;
    revenue: number;
    profit: number;
  }>;
  bottom_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    qty: number;
    revenue: number;
    profit: number;
  }>;
  sku_concentration?: number;
  high_return_skus: Array<{
    sku: string;
    name: string;
    return_rate: number;
    return_amount: number;
  }>;
  recommendations: AgentRecommendation[];
}

export interface InventoryAgentResult {
  agent_type: string;
  summary: {
    health_score: number;
    total_skus: number;
    healthy_count: number;
    stockout_count: number;
    low_stock_count: number;
    stale_count: number;
    overstock_count: number;
    total_capital: number;
    inv_date: string;
  };
  stockout_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    effective: number;
    daily_rate: number;
    safety_stock: number;
    capital: number;
    sold_qty: number;
  }>;
  low_stock_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    daily_rate: number;
    safety_stock: number;
    capital: number;
  }>;
  stale_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    capital: number;
    sold_qty: number;
  }>;
  overstock_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    turnover_days: number;
    capital: number;
  }>;
  recommendations: AgentRecommendation[];
}

export interface ProcurementAgentResult {
  agent_type: string;
  summary: {
    urgent_count: number;
    normal_count: number;
    planned_count: number;
    urgent_value: number;
    normal_value: number;
    total_reorder_value: number;
    total_reorder_qty?: number;
    fast_moving_count?: number;
    slow_moving_count?: number;
  };
  urgent_reorders: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    inbound: number;
    daily_rate: number;
    safety_stock: number;
    reorder_qty: number;
    unit_cost: number;
    reorder_value: number;
    days_of_supply: number;
  }>;
  normal_reorders: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    daily_rate: number;
    reorder_qty: number;
    reorder_value: number;
    days_of_supply: number;
  }>;
  recommendations: AgentRecommendation[];
}

export interface FinanceAgentResult {
  agent_type: string;
  summary: {
    revenue: number;
    cost: number;
    profit: number;
    commission: number;
    gross_margin: number;
    cost_ratio: number;
    commission_ratio: number;
    ship_margin: number;
  };
  by_brand: Array<{
    brand: string;
    revenue: number;
    cost: number;
    profit: number;
    margin: number;
  }>;
  loss_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    qty: number;
    revenue: number;
    cost: number;
    profit: number;
  }>;
  total_loss: number;
  no_cost_sku_count: number;
  no_cost_revenue: number;
  recommendations: AgentRecommendation[];
}

export interface OperationAgentResult {
  agent_type: string;
  summary: {
    ship_amount: number;
    net_amount: number;
    discount_amount: number;
    discount_rate: number;
    profit: number;
    ship_qty: number;
    net_qty: number;
    avg_order_value: number;
  };
  low_margin_skus: Array<{
    sku: string;
    name: string;
    brand: string | null;
    qty: number;
    revenue: number;
    cost: number;
    profit: number;
    margin: number;
    suggested_price: number;
  }>;
  promo_opportunities: Array<{
    sku: string;
    name: string;
    brand: string | null;
    available: number;
    capital: number;
    monthly_sales: number;
    suggested_action: string;
  }>;
  recommendations: AgentRecommendation[];
}

export interface CEOAgentResult {
  agent_type: string;
  summary: {
    overall_status: 'excellent' | 'normal' | 'warning' | 'critical';
    status_text: string;
    revenue: number;
    profit: number;
    gross_margin: number;
    return_rate: number;
    ship_qty: number;
    stockout_count: number;
    loss_count: number;
    total_loss: number;
    stale_count: number;
    health_score: number;
    urgent_reorder_count: number;
    urgent_reorder_value: number;
    no_cost_count: number;
    discount_rate: number;
    period: string;
    mom_revenue_change?: number;
  };
  questions: string[];
  actions: string[];
  high_priority_alerts: Array<{
    agent: string;
    text: string;
  }>;
  agent_results: {
    sales: SalesAgentResult;
    inventory: InventoryAgentResult;
    procurement: ProcurementAgentResult;
    finance: FinanceAgentResult;
    operation: OperationAgentResult;
  };
}

export interface AllAgentsResult {
  period: string;
  brand: string | null;
  ceo: CEOAgentResult;
  agents: {
    sales: SalesAgentResult;
    inventory: InventoryAgentResult;
    procurement: ProcurementAgentResult;
    finance: FinanceAgentResult;
    operation: OperationAgentResult;
  };
}

// ===== Analysis =====

export interface ABCItem {
  sku: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  qty: number;
  revenue: number;
  profit: number;
  cost: number;
  margin_pct: number;
  cum_pct: number;
  grade: 'A' | 'B' | 'C';
}

export interface ABCAnalysis {
  summary: {
    total_skus: number;
    a_count: number;
    b_count: number;
    c_count: number;
    total_revenue: number;
    total_profit: number;
    a_revenue: number;
    b_revenue: number;
    c_revenue: number;
    a_profit: number;
    b_profit: number;
    c_profit: number;
    a_revenue_pct: number;
    b_revenue_pct: number;
    c_revenue_pct: number;
  };
  items: ABCItem[];
}

export interface GMROIItem {
  sku: string;
  product_name: string;
  brand: string | null;
  category: string | null;
  available_qty: number;
  effective_qty: number;
  unit_cost: number;
  inv_cost: number;
  qty: number;
  revenue: number;
  profit: number;
  gmroi: number | null;
  turnover: number | null;
  margin_pct: number;
  status: 'no_inventory' | 'good' | 'poor';
}

export interface GMROIAnalysis {
  summary: {
    total_skus: number;
    total_inv_cost: number;
    total_profit: number;
    overall_gmroi: number;
    positive_gmroi_count: number;
    negative_gmroi_count: number;
    no_inventory_count: number;
  };
  items: GMROIItem[];
}

export interface ForecastHistoryItem {
  period: string;
  revenue: number;
  profit: number;
  qty: number;
  cost: number;
  ship_qty: number;
  return_qty: number;
  is_outlier?: boolean;
}

export interface ForecastItem {
  period: string;
  revenue: number;
  profit: number;
  cost: number;
  is_forecast: boolean;
  revenue_lower?: number;
  revenue_upper?: number;
}

export interface SalesForecast {
  history: ForecastHistoryItem[];
  forecast: ForecastItem[];
  trend: {
    slope: number;
    intercept: number;
    slope_profit: number;
    intercept_profit: number;
    avg_growth_rate: number;
    r_squared: number;
  };
  summary: {
    next_month_revenue: number;
    next_month_profit: number;
    confidence: 'high' | 'medium' | 'low';
    data_points: number;
    effective_data_points?: number;
    outlier_periods?: string[];
    confidence_interval?: string;
    trend_direction: 'up' | 'down' | 'flat';
  };
}

export interface CashflowItem {
  period: string;
  inflow: number;
  outflow_cost: number;
  outflow_expense: number;
  net_cashflow: number;
  cumulative: number;
  is_forecast?: boolean;
}

export interface CashflowForecast {
  history: CashflowItem[];
  forecast: CashflowItem[];
  expense_breakdown: Array<{
    type: string;
    monthly_avg: number;
    pct: number;
  }>;
  has_expense_data: boolean;
  summary: {
    next_month_inflow: number;
    next_month_outflow: number;
    next_month_net: number;
    avg_monthly_expense: number;
    forecast_total_net: number;
    trend: string;
  };
}

export interface IntervalItem {
  discount_range: string;
  sku_count: number;
  revenue: number;
  profit: number;
  cost: number;
  qty: number;
  margin_pct: number;
  avg_profit_per_sku: number;
}

export interface OptimalInterval {
  intervals: IntervalItem[];
  optimal: IntervalItem | null;
}

// ===== Store Channel Analysis =====

export interface StoreProductDetail {
  product_id: string;
  sku: string;
  product_name: string;
  category: string | null;
  brand: string | null;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  net_revenue: number;
  net_cost: number;
  commission_cost: number;
  net_profit: number;
  gross_margin_pct: number;
}

export interface StoreProductSummary {
  total_revenue: number;
  total_cost: number;
  total_profit: number;
  gross_margin_pct: number;
  sku_count: number;
}

export interface StoreMonthlyData {
  store_id: string;
  store_name: string;
  platform: string;
  channel: string | null;
  months: Record<string, {
    revenue: number;
    cost: number;
    profit: number;
    ship_qty: number;
    return_qty: number;
    net_qty: number;
  }>;
  total_revenue: number;
  total_profit: number;
}

export interface ChannelSales {
  channel: string;
  store_count: number;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  total_revenue: number;
  total_cost: number;
  commission_cost: number;
  gross_profit: number;
  gross_margin_pct: number;
}

export interface CrossSales {
  platform: string;
  channel: string;
  revenue: number;
  profit: number;
  store_count: number;
}

// ===== 实时销售分析 =====
export interface RealtimeDaySummary {
  date: string;
  orders: number;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
  receivable?: number;
  goods_amount?: number;
  has_data: boolean;
}

export interface RealtimeOverview {
  today: RealtimeDaySummary;
  yesterday: RealtimeDaySummary;
  period: {
    orders: number;
    quantity: number;
    sell_amount: number;
    cost_amount: number;
    gross_profit: number;
    margin_pct: number;
    receivable: number;
    goods_amount: number;
    avg_daily_orders: number;
    avg_daily_sell: number;
  };
  period_daily: RealtimeDaySummary[];
  available_dates: string[];
  latest_date: string | null;
  days: number;
}

export interface RealtimeTrendItem {
  date: string;
  orders: number;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
}

export interface RealtimeTopSku {
  spec_no: string;
  goods_name: string;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
  order_count: number;
  days_sold: number;
  shop_count: number;
  shops: string[];
  warehouses: string[];
}

export interface RealtimeByShop {
  shop: string;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
  order_count: number;
  sku_count: number;
}

export interface RealtimeByWarehouse {
  warehouse: string;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
  order_count: number;
  sku_count: number;
}

export interface RealtimeSkuDetail {
  spec_no: string;
  goods_name: string;
  quantity: number;
  total_sell_amount: number;
  total_cost_amount: number;
  avg_sell_price: number;
  avg_cost_price: number;
  order_count: number;
  shops: string[];
  warehouses: string[];
}

export interface RealtimeDailyDetail {
  date: string;
  has_data: boolean;
  fetch_time: string;
  total_orders: number;
  total_quantity: number;
  total_sell_amount: number;
  total_cost_amount: number;
  order_level_receivable: number;
  order_level_goods_amount: number;
  skipped_sku: number;
  skipped_wh: number;
  details: RealtimeSkuDetail[];
}

export interface RealtimeMonthlyItem {
  month: string;
  orders: number;
  quantity: number;
  sell_amount: number;
  cost_amount: number;
  gross_profit: number;
  margin_pct: number;
  receivable: number;
  days_with_data: number;
  avg_daily_sell: number;
}
