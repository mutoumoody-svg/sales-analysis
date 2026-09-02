import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const adminKey = sessionStorage.getItem('admin_api_key') || import.meta.env.VITE_ADMIN_API_KEY;
  if (adminKey) config.headers.set('X-Admin-Key', adminKey);
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('API Error:', err.message);
    return Promise.reject(err);
  }
);

export default api;
