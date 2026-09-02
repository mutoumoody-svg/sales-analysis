import api from './client';

// ===== Sales =====
export const salesApi = {
  periods: () => api.get('/sales/periods'),
  overview: (params?: Record<string, unknown>) => api.get('/sales/overview', { params }),
  summary: (params?: Record<string, unknown>) => api.get('/sales/summary', { params }),
  byStore: (params?: Record<string, unknown>) => api.get('/sales/by-store', { params }),
  byProduct: (params?: Record<string, unknown>) => api.get('/sales/by-product', { params }),
  dailyTrend: (params?: Record<string, unknown>) => api.get('/sales/daily-trend', { params }),
  byPlatform: (params?: Record<string, unknown>) => api.get('/sales/by-platform', { params }),
  byCategory: (params?: Record<string, unknown>) => api.get('/sales/by-category', { params }),
  storeProducts: (params: Record<string, unknown>) => api.get('/sales/store-products', { params }),
  storeMonthly: (params?: Record<string, unknown>) => api.get('/sales/store-monthly', { params }),
  byChannel: (params?: Record<string, unknown>) => api.get('/sales/by-channel', { params }),
  monthlyCompare: (params: Record<string, unknown>) => api.get('/sales/monthly-compare', { params }),
  stores: (params?: Record<string, unknown>) => api.get('/stores', { params }),
  products: (params?: Record<string, unknown>) => api.get('/products', { params }),
  categories: (params?: Record<string, unknown>) => api.get('/products/categories', { params }),
  brands: (params?: Record<string, unknown>) => api.get('/brands', { params }),
};

// ===== Profit =====
export const profitApi = {
  summary: (params?: Record<string, unknown>) => api.get('/profit/summary', { params }),
  byStore: (params?: Record<string, unknown>) => api.get('/profit/by-store', { params }),
  byProduct: (params?: Record<string, unknown>) => api.get('/profit/by-product', { params }),
  dailyTrend: (params?: Record<string, unknown>) => api.get('/profit/daily-trend', { params }),
  bySku: (sku: string, params?: Record<string, unknown>) => api.get(`/profit/by-sku/${sku}`, { params }),
  lowMargin: (params?: Record<string, unknown>) => api.get('/profit/low-margin', { params }),
};

// ===== Inventory =====
export const inventoryApi = {
  health: (params?: Record<string, unknown>) => api.get('/inventory/health', { params }),
  analysis: (params?: Record<string, unknown>) => api.get('/inventory/analysis', { params }),
  wangdianSyncStatus: () => api.get('/inventory/wangdian-sync-status'),
  syncFromWangdian: () => api.post('/inventory/sync-from-wangdian', {}, { timeout: 120000 }),
};

// ===== Dashboard =====
export const dashboardApi = {
  healthIndex: (params?: Record<string, unknown>) => api.get('/dashboard/health-index', { params }),
  ceoReport: (params?: Record<string, unknown>) => api.get('/dashboard/ceo-report', { params }),
};

// ===== AI Agents =====
export const agentApi = {
  runAll: (params?: Record<string, unknown>) => api.get('/agents/run', { params, timeout: 120000 }),
  ceoReport: (params?: Record<string, unknown>) => api.get('/agents/ceo-report', { params, timeout: 120000 }),
  sales: (params?: Record<string, unknown>) => api.get('/agents/sales', { params }),
  inventory: (params?: Record<string, unknown>) => api.get('/agents/inventory', { params }),
  procurement: (params?: Record<string, unknown>) => api.get('/agents/procurement', { params }),
  finance: (params?: Record<string, unknown>) => api.get('/agents/finance', { params }),
  operation: (params?: Record<string, unknown>) => api.get('/agents/operation', { params }),
  recommendations: (params?: Record<string, unknown>) => api.get('/agents/recommendations', { params }),
};

// ===== Import =====
export const importApi = {
  status: () => api.get('/import/status'),
  uploadDetail: (file: File, period?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (period) formData.append('period', period);
    return api.post('/import/detail', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000,
    });
  },
  uploadSummary: (file: File, period?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (period) formData.append('period', period);
    return api.post('/import/summary', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180000,
    });
  },
  uploadInventory: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/import/inventory', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
  },
};

// ===== Analysis =====
export const analysisApi = {
  abc: (params?: Record<string, unknown>) => api.get('/analysis/abc', { params }),
  gmroi: (params?: Record<string, unknown>) => api.get('/analysis/gmroi', { params }),
  forecast: (params?: Record<string, unknown>) => api.get('/analysis/forecast', { params }),
  cashflow: (params?: Record<string, unknown>) => api.get('/analysis/cashflow', { params }),
  interval: (params?: Record<string, unknown>) => api.get('/analysis/interval', { params }),
};

// ===== Export =====
export const exportApi = {
  abc: (params?: Record<string, unknown>) =>
    api.get('/export/abc', { params, responseType: 'blob', timeout: 60000 }),
  gmroi: (params?: Record<string, unknown>) =>
    api.get('/export/gmroi', { params, responseType: 'blob', timeout: 60000 }),
  forecast: (params?: Record<string, unknown>) =>
    api.get('/export/forecast', { params, responseType: 'blob', timeout: 60000 }),
  cashflow: (params?: Record<string, unknown>) =>
    api.get('/export/cashflow', { params, responseType: 'blob', timeout: 60000 }),
  sales: (params?: Record<string, unknown>) =>
    api.get('/export/sales', { params, responseType: 'blob', timeout: 60000 }),
  profit: (params?: Record<string, unknown>) =>
    api.get('/export/profit', { params, responseType: 'blob', timeout: 60000 }),
  inventory: (params?: Record<string, unknown>) =>
    api.get('/export/inventory', { params, responseType: 'blob', timeout: 60000 }),
};

// ===== Realtime Sales =====
export const realtimeApi = {
  overview: (days: number = 7) => api.get('/realtime/overview', { params: { days } }),
  trend: (days: number = 30) => api.get('/realtime/trend', { params: { days } }),
  topSkus: (days: number = 7, limit: number = 20) => api.get('/realtime/top-skus', { params: { days, limit } }),
  byShop: (days: number = 7) => api.get('/realtime/by-shop', { params: { days } }),
  byWarehouse: (days: number = 7) => api.get('/realtime/by-warehouse', { params: { days } }),
  dailyDetail: (date: string) => api.get('/realtime/daily-detail', { params: { date } }),
  monthlySummary: () => api.get('/realtime/monthly-summary'),
};

// ===== Shop Daily (店铺订单日报) =====
export const shopDailyApi = {
  overview: (days: number = 7, shop: string = '慕咖') => api.get('/shop-daily/overview', { params: { days, shop } }),
  trend: (days: number = 30, shop: string = '慕咖') => api.get('/shop-daily/trend', { params: { days, shop } }),
  byShop: (days: number = 7, shop: string = '慕咖') => api.get('/shop-daily/by-shop', { params: { days, shop } }),
  topSkus: (days: number = 30, shop: string = '慕咖', limit: number = 20) => api.get('/shop-daily/top-skus', { params: { days, shop, limit } }),
  dailyDetail: (date: string, shop: string = '慕咖') => api.get('/shop-daily/daily-detail', { params: { date, shop } }),
  availableDates: (shop: string = '慕咖') => api.get('/shop-daily/available-dates', { params: { shop } }),
};

// ===== Operations governance =====
export const operationsApi = {
  quality: (params?: Record<string, unknown>) => api.get('/operations/data-quality', { params }),
  costs: (params?: Record<string, unknown>) => api.get('/operations/costs', { params }),
  saveCost: (data: Record<string, unknown>) => api.post('/operations/costs', data),
  deleteCost: (id: string) => api.delete(`/operations/costs/${id}`),
  recalculateCosts: (params?: Record<string, unknown>) => api.post('/operations/costs/recalculate', null, { params, timeout: 120000 }),
  purchasePlans: (params?: Record<string, unknown>) => api.get('/operations/purchase-plans', { params }),
  generatePurchasePlans: (params?: Record<string, unknown>) => api.post('/operations/purchase-plans/generate', null, { params, timeout: 120000 }),
  updatePurchasePlan: (id: string, data: Record<string, unknown>) => api.patch(`/operations/purchase-plans/${id}`, data),
  dailyAlerts: () => api.get('/operations/daily-alerts'),
};

// ===== Confirmed monthly accounting from sales.riverline.com.cn =====
export const monthlyAccountingApi = {
  periods: () => api.get('/monthly-accounting/periods'),
  summary: (period: string) => api.get('/monthly-accounting/summary', { params: { period } }),
  sync: (period: string) => api.post('/monthly-accounting/sync', null, { params: { period }, timeout: 120000 }),
};
