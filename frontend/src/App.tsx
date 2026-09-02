import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Sales from './pages/Sales';
import Profit from './pages/Profit';
import Inventory from './pages/Inventory';
import Analysis from './pages/Analysis';
import ImportPage from './pages/Import';
import Agents from './pages/Agents';
import StoreChannel from './pages/StoreChannel';
import RealTimeSales from './pages/RealTimeSales';
import ShopDaily from './pages/ShopDaily';
import Operations from './pages/Operations';
import MonthlyAccounting from './pages/MonthlyAccounting';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="realtime" element={<RealTimeSales />} />
        <Route path="shop-daily" element={<ShopDaily />} />
        <Route path="sales" element={<Sales />} />
        <Route path="store-channel" element={<StoreChannel />} />
        <Route path="profit" element={<Profit />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="analysis" element={<Analysis />} />
        <Route path="agents" element={<Agents />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="operations" element={<Operations />} />
        <Route path="monthly-accounting" element={<MonthlyAccounting />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
