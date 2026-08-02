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
};

// ===== Dashboard =====
export const dashboardApi = {
  healthIndex: (params?: Record<string, unknown>) => api.get('/dashboard/health-index', { params }),
  ceoReport: (params?: Record<string, unknown>) => api.get('/dashboard/ceo-report', { params }),
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
