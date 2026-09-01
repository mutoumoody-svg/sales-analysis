import { useEffect, useMemo, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, Input, Spin, Segmented, Tabs, Tooltip, Select, Space, Button, Empty, Alert, message } from 'antd';
import { ReloadOutlined, ClearOutlined, DownloadOutlined, RiseOutlined, FallOutlined, MinusOutlined, SyncOutlined, ApiOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { Resizable } from 'react-resizable';
import 'react-resizable/css/styles.css';
import { inventoryApi, exportApi } from '../api';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import type { InventoryHealth, InventoryItem, InventoryAnalysis, InventoryAnalysisItem, WangdianSyncStatus } from '../types';
import { formatCurrency, formatNumber } from '../utils/format';

// ============ 可拖拽列宽的表头 ============
// 把这个组件放在 Inventory 组件外，避免每次 render 重新创建
interface ResizableHeaderProps {
  width?: number;
  onResize?: (e: React.SyntheticEvent, data: { size: { width: number } }) => void;
  [key: string]: unknown;
}

const ResizableHeader: React.FC<ResizableHeaderProps> = ({ width, onResize, ...restProps }) => {
  if (!width) {
    return <th {...(restProps as React.ThHTMLAttributes<HTMLTableCellElement>)} />;
  }
  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="react-resizable-handle"
          style={{
            position: 'absolute',
            right: -4,
            bottom: 0,
            top: 0,
            width: 8,
            cursor: 'col-resize',
            background: 'transparent',
            zIndex: 1,
          }}
          onClick={(e) => e.stopPropagation()}
        />
      }
      onResize={onResize as never}
      draggableOpts={{ enableUserSelectHack: false }}
      minConstraints={[60, 0]}
    >
      <th {...(restProps as React.ThHTMLAttributes<HTMLTableCellElement>)} style={{ position: 'relative', ...((restProps as { style?: React.CSSProperties }).style || {}) }} />
    </Resizable>
  );
};

const riskConfig: Record<string, { color: string; label: string; tagColor: string }> = {
  stockout: { color: '#ff4d4f', label: '缺货', tagColor: 'red' },
  low_stock: { color: '#fa8c16', label: '低库存', tagColor: 'orange' },
  overstock: { color: '#1677ff', label: '积压', tagColor: 'blue' },
  healthy: { color: '#52c41a', label: '健康', tagColor: 'green' },
};

const statusConfig: Record<string, { color: string; label: string; tagColor: string }> = {
  stockout: { color: '#ff4d4f', label: '缺货', tagColor: 'red' },
  stale: { color: '#8c8c8c', label: '滞销', tagColor: 'default' },
  reorder: { color: '#fa8c16', label: '需补货', tagColor: 'orange' },
  overstock: { color: '#1677ff', label: '积压', tagColor: 'blue' },
  healthy: { color: '#52c41a', label: '健康', tagColor: 'green' },
};

const brandOptions = [
  { label: '全部品牌', value: '' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

export default function Inventory() {
  const [brand, setBrand] = useState<string>('');
  const { periods, month, setMonth } = usePeriods();
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [healthData, setHealthData] = useState<InventoryHealth | null>(null);
  const [analysisData, setAnalysisData] = useState<InventoryAnalysis | null>(null);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  // 补货建议 Tab 内的优先级筛选（all / urgent / normal）
  const [reorderFilter, setReorderFilter] = useState<'all' | 'urgent' | 'normal'>('all');
  // 补货建议 Tab 内的排序预设（卡片点击触发）
  const [reorderSort, setReorderSort] = useState<'default' | 'qty' | 'value'>('default');
  // 补货建议表格列宽（用户拖拽调整后保存）
  const [reorderColumnWidths, setReorderColumnWidths] = useState<Record<string, number>>({});
  // 补货建议表格多选筛选条件（与上方快捷筛选并存叠加）
  const [reorderBrandFilter, setReorderBrandFilter] = useState<string[]>([]);
  const [reorderTurnoverFilter, setReorderTurnoverFilter] = useState<string[]>([]); // fast/slow
  const [reorderTrendFilter, setReorderTrendFilter] = useState<string[]>([]); // up/down/flat
  const [reorderPriorityFilter, setReorderPriorityFilter] = useState<string[]>([]); // urgent/normal/planned
  const [reorderSafetyFilter, setReorderSafetyFilter] = useState<string[]>([]); // 1.7/1.3
  // 列点击触发的排序键（与 reorderSort 卡片预设共存）
  const [reorderColumnSort, setReorderColumnSort] = useState<{ key: string; order: 'ascend' | 'descend' } | null>(null);

  // 旺店通 API 同步状态
  const [wangdianStatus, setWangdianStatus] = useState<WangdianSyncStatus | null>(null);
  const [wangdianSyncing, setWangdianSyncing] = useState(false);

  // 明细表筛选条件
  const [warehouseFilter, setWarehouseFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [costFilter, setCostFilter] = useState<string>(''); // all / with / without
  const [amountBucket, setAmountBucket] = useState<string>(''); // 金额区间

  useEffect(() => {
    if (!month) return;
    setLoading(true);
    const params: Record<string, string> = { month };
    if (brand) params.brand = brand;
    Promise.all([
      inventoryApi.health(brand ? { brand } : {}),
      inventoryApi.analysis(params),
    ])
      .then(([h, a]) => {
        setHealthData(h.data.data);
        setAnalysisData(a.data.data);
      })
      .finally(() => setLoading(false));
  }, [brand, month]);

  // 拉取旺店通同步状态（只在挂载时拉一次）
  useEffect(() => {
    inventoryApi.wangdianSyncStatus()
      .then((r) => setWangdianStatus(r.data.data))
      .catch(() => {});
  }, []);

  // 过滤数据 —— 明细表改用 analysisData.items（包含 unit_cost/capital_occupied）
  // 注意：useMemo 必须在早返回之前，保持 hooks 调用顺序稳定
  const allAnalysisItems = analysisData?.items || [];
  const warehouseOptions = useMemo(
    () => Array.from(new Set(allAnalysisItems.map((i) => i.warehouse))).sort(),
    [allAnalysisItems]
  );

  const filteredOverview = useMemo(() => {
    return allAnalysisItems.filter((item) => {
      const matchSearch = !search ||
        item.sku.toLowerCase().includes(search.toLowerCase()) ||
        item.product_name.toLowerCase().includes(search.toLowerCase());
      const matchWarehouse = warehouseFilter.length === 0 || warehouseFilter.includes(item.warehouse);
      const matchStatus = !statusFilter || item.status === statusFilter;
      const hasCost = item.unit_cost > 0;
      const matchCost = !costFilter ||
        (costFilter === 'with' && hasCost) ||
        (costFilter === 'without' && !hasCost);
      let matchAmount = true;
      if (amountBucket) {
        const v = item.capital_occupied;
        if (amountBucket === '0') matchAmount = v === 0;
        else if (amountBucket === '1w') matchAmount = v > 0 && v < 10000;
        else if (amountBucket === '10w') matchAmount = v >= 10000 && v < 100000;
        else if (amountBucket === '50w') matchAmount = v >= 100000 && v < 500000;
        else if (amountBucket === '50w+') matchAmount = v >= 500000;
      }
      return matchSearch && matchWarehouse && matchStatus && matchCost && matchAmount;
    });
  }, [allAnalysisItems, search, warehouseFilter, statusFilter, costFilter, amountBucket]);

  // 筛选后汇总
  const overviewSummary = useMemo(() => {
    const totalCapital = filteredOverview.reduce((s, i) => s + i.capital_occupied, 0);
    const totalQty = filteredOverview.reduce((s, i) => s + i.effective_qty, 0);
    const withCostCount = filteredOverview.filter((i) => i.unit_cost > 0).length;
    return {
      totalCapital,
      totalQty,
      withCostCount,
      skuCount: filteredOverview.length,
    };
  }, [filteredOverview]);

  // 补货建议全量 + 优先级筛选（保持 hooks 顺序稳定，置于早返回之前）
  const reorderItems = useMemo(
    () => allAnalysisItems.filter((i) => i.needs_reorder).sort((a, b) => b.reorder_qty - a.reorder_qty),
    [allAnalysisItems]
  );
  const filteredReorderItems = useMemo(() => {
    let items = reorderItems;
    // 卡片点击：紧急/常规快捷筛选
    if (reorderFilter === 'urgent') items = items.filter((i) => i.priority === 'urgent');
    if (reorderFilter === 'normal') items = items.filter((i) => i.priority === 'normal');
    // 搜索过滤（SKU/商品名）
    if (search) {
      const s = search.toLowerCase();
      items = items.filter((i) =>
        i.sku.toLowerCase().includes(s) || i.product_name.toLowerCase().includes(s)
      );
    }
    // 表格上方多选筛选
    if (reorderBrandFilter.length > 0) {
      items = items.filter((i) => reorderBrandFilter.includes(i.brand || ''));
    }
    if (reorderTurnoverFilter.length > 0) {
      items = items.filter((i) => reorderTurnoverFilter.includes(i.turnover_category || ''));
    }
    if (reorderTrendFilter.length > 0) {
      items = items.filter((i) => reorderTrendFilter.includes(i.trend_direction || ''));
    }
    if (reorderPriorityFilter.length > 0) {
      items = items.filter((i) => reorderPriorityFilter.includes(i.priority || ''));
    }
    if (reorderSafetyFilter.length > 0) {
      items = items.filter((i) => reorderSafetyFilter.includes(String(i.safety_factor)));
    }
    // 排序：列点击 > 卡片预设 > 默认（按补货量降序）
    if (reorderColumnSort) {
      const { key, order } = reorderColumnSort;
      const dir = order === 'ascend' ? 1 : -1;
      items = [...items].sort((a, b) => {
        const av = (a as unknown as Record<string, unknown>)[key];
        const bv = (b as unknown as Record<string, unknown>)[key];
        if (av === bv) return 0;
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
        return String(av).localeCompare(String(bv)) * dir;
      });
    } else if (reorderSort === 'qty') {
      items = [...items].sort((a, b) => b.reorder_qty - a.reorder_qty);
    } else if (reorderSort === 'value') {
      items = [...items].sort((a, b) => b.reorder_value - a.reorder_value);
    } else {
      items = [...items].sort((a, b) => b.reorder_qty - a.reorder_qty);
    }
    return items;
  }, [
    reorderItems, reorderFilter, reorderSort, search,
    reorderBrandFilter, reorderTurnoverFilter, reorderTrendFilter,
    reorderPriorityFilter, reorderSafetyFilter, reorderColumnSort,
  ]);

  // 周转分析 Tab 数据
  const filteredAnalysis = useMemo(() => {
    return allAnalysisItems.filter((item) => {
      const matchSearch = !search ||
        item.sku.toLowerCase().includes(search.toLowerCase()) ||
        item.product_name.toLowerCase().includes(search.toLowerCase());
      return matchSearch;
    });
  }, [allAnalysisItems, search]);

  // 补货建议表格上方多选筛选的 options（从当前补货数据里提取）
  const reorderBrandOptions = useMemo(
    () => Array.from(new Set(reorderItems.map((i) => i.brand).filter(Boolean))).sort(),
    [reorderItems]
  );

  // 滞销分析 Tab 数据
  const staleItems = useMemo(() => {
    let items = allAnalysisItems.filter((i) => i.is_stale);
    if (search) {
      const s = search.toLowerCase();
      items = items.filter((i) =>
        i.sku.toLowerCase().includes(s) || i.product_name.toLowerCase().includes(s)
      );
    }
    return items;
  }, [allAnalysisItems, search]);

  // 补货建议列（带可拖拽列宽 + 每列可点击排序）
  // 注意：必须放在 if(loading) return 之前，保持 hooks 顺序稳定
  // 排序键 lookup（字符串字段按业务语义排序）
  const trendSortOrder: Record<string, number> = { down: 1, flat: 2, up: 3 };
  const turnoverCatSortOrder: Record<string, number> = { fast: 1, slow: 2 };
  const prioritySortOrder: Record<string, number> = { urgent: 1, normal: 2, planned: 3, sufficient: 4 };
  const safetyFactorSortOrder: Record<string, number> = { '1.3': 1, '1.7': 2 };

  // 取列的当前 sortOrder（高亮表头排序箭头）
  const colSort = (key: string) =>
    reorderColumnSort?.key === key ? reorderColumnSort.order : undefined;

  const reorderColumnDefs: Array<Record<string, unknown>> = [
    {
      title: 'SKU', dataIndex: 'sku', width: 110, fixed: 'left' as const,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.sku.localeCompare(b.sku),
      sortOrder: colSort('sku'),
    },
    {
      title: '商品名称', dataIndex: 'product_name', width: 200,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.product_name.localeCompare(b.product_name),
      sortOrder: colSort('product_name'),
      // 自动换行展示完整：去掉 ellipsis，让 white-space 走 normal
    },
    {
      title: '品牌', dataIndex: 'brand', width: 90,
      render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-',
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.brand || '').localeCompare(b.brand || ''),
      sortOrder: colSort('brand'),
    },
    {
      title: '当前库存', dataIndex: 'available_qty', width: 80,
      render: (v: number) => <span style={{ color: v === 0 ? '#ff4d4f' : '#fa8c16' }}>{formatNumber(v)}</span>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.available_qty - b.available_qty,
      sortOrder: colSort('available_qty'),
    },
    {
      title: '加权日均', dataIndex: 'weighted_daily_rate', width: 90,
      render: (v: number) => v > 0 ? <strong>{v.toFixed(2)}</strong> : '-',
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.weighted_daily_rate - b.weighted_daily_rate,
      sortOrder: colSort('weighted_daily_rate'),
    },
    {
      title: '趋势', dataIndex: 'trend_direction', width: 70,
      render: (v: string, record: InventoryAnalysisItem) => {
        if (v === 'up') return <Tooltip title={`+${record.trend_pct}%`}><Tag icon={<RiseOutlined />} color="green">上升</Tag></Tooltip>;
        if (v === 'down') return <Tooltip title={`${record.trend_pct}%`}><Tag icon={<FallOutlined />} color="red">下降</Tag></Tooltip>;
        return <Tag icon={<MinusOutlined />}>平稳</Tag>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (trendSortOrder[a.trend_direction] || 0) - (trendSortOrder[b.trend_direction] || 0),
      sortOrder: colSort('trend_direction'),
    },
    {
      title: '周转天数', dataIndex: 'turnover_days', width: 85,
      render: (v: number | null) => {
        if (v === null) return '-';
        const color = v < 30 ? '#52c41a' : v < 60 ? '#fa8c16' : '#ff4d4f';
        return <span style={{ color }}>{v}天</span>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (a.turnover_days ?? 99999) - (b.turnover_days ?? 99999),
      sortOrder: colSort('turnover_days'),
    },
    {
      title: '周转分类', dataIndex: 'turnover_category', width: 80,
      render: (v: string) => v === 'fast' ? <Tag color="orange">快消</Tag> : <Tag color="blue">慢消</Tag>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (turnoverCatSortOrder[a.turnover_category] || 0) - (turnoverCatSortOrder[b.turnover_category] || 0),
      sortOrder: colSort('turnover_category'),
    },
    {
      title: '安全系数', dataIndex: 'safety_factor', width: 75,
      render: (v: number) => <Tag color={v === 1.7 ? 'orange' : 'blue'}>{v}x</Tag>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (safetyFactorSortOrder[String(a.safety_factor)] || 0) - (safetyFactorSortOrder[String(b.safety_factor)] || 0),
      sortOrder: colSort('safety_factor'),
    },
    {
      title: '安全库存', dataIndex: 'safety_stock', width: 80,
      render: (v: number) => <strong>{formatNumber(v)}</strong>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.safety_stock - b.safety_stock,
      sortOrder: colSort('safety_stock'),
    },
    {
      title: '建议补货量', dataIndex: 'reorder_qty', width: 100,
      render: (v: number) => v > 0 ? <Tag color="orange">{formatNumber(v)}件</Tag> : <Tag color="green">充足</Tag>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.reorder_qty - b.reorder_qty,
      sortOrder: colSort('reorder_qty'),
    },
    {
      title: '采购金额', dataIndex: 'reorder_value', width: 100,
      render: (v: number) => v > 0 ? <span style={{ color: '#1677ff', fontWeight: 600 }}>¥{formatNumber(v)}</span> : '-',
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.reorder_value - b.reorder_value,
      sortOrder: colSort('reorder_value'),
    },
    {
      title: '可供应天数', dataIndex: 'days_of_supply', width: 90,
      render: (v: number | null) => {
        if (v === null) return '-';
        const color = v < 7 ? '#ff4d4f' : v < 30 ? '#fa8c16' : '#52c41a';
        return <span style={{ color }}>{v}天</span>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (a.days_of_supply ?? 99999) - (b.days_of_supply ?? 99999),
      sortOrder: colSort('days_of_supply'),
    },
    {
      title: '优先级', dataIndex: 'priority', width: 80,
      render: (v: string) => {
        if (v === 'urgent') return <Tag color="red">紧急</Tag>;
        if (v === 'normal') return <Tag color="orange">常规</Tag>;
        if (v === 'planned') return <Tag color="blue">计划</Tag>;
        return <Tag color="green">充足</Tag>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) =>
        (prioritySortOrder[a.priority] || 0) - (prioritySortOrder[b.priority] || 0),
      sortOrder: colSort('priority'),
    },
  ];

  // 处理列宽拖拽
  const handleReorderResize = (key: string) =>
    (_e: React.SyntheticEvent, { size }: { size: { width: number } }) => {
      setReorderColumnWidths((prev) => ({ ...prev, [key]: size.width }));
    };

  // 把列定义加上可拖拽的 onHeaderCell（hooks 顺序：必须在 if(loading) return 之前）
  const reorderColumns = useMemo(
    () =>
      reorderColumnDefs.map((col) => {
        const dataIndex = col.dataIndex as string;
        const defaultWidth = (col.width as number | undefined) ?? 100;
        const currentWidth = reorderColumnWidths[dataIndex] ?? defaultWidth;
        return {
          ...col,
          width: currentWidth,
          onHeaderCell: () => ({
            width: currentWidth,
            onResize: handleReorderResize(dataIndex),
          }),
        };
      }),
    [reorderColumnWidths]
  );

// 触发旺店通API → sales-analysis 库存同步
  const handleSyncFromWangdian = async () => {
    setWangdianSyncing(true);
    try {
      const r = await inventoryApi.syncFromWangdian();
      const result = r.data;
      if (result.status === 'success') {
        message.success(result.message);
        // 刷新同步状态 + 重新加载库存数据
        const sr = await inventoryApi.wangdianSyncStatus();
        setWangdianStatus(sr.data.data);
        // 重新加载页面数据以反映新库存
        const params: Record<string, string> = {};
        if (month) params.month = month;
        if (brand) params.brand = brand;
        const [h, a] = await Promise.all([
          inventoryApi.health(brand ? { brand } : {}),
          inventoryApi.analysis(params),
        ]);
        setHealthData(h.data.data);
        setAnalysisData(a.data.data);
      } else {
        message.warning(result.message || '同步失败');
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      message.error(err.response?.data?.detail || err.message || '旺店通同步请求失败');
    } finally {
      setWangdianSyncing(false);
    }
  };

  const resetOverviewFilters = () => {
    setWarehouseFilter([]);
    setStatusFilter('');
    setCostFilter('');
    setAmountBucket('');
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', padding: 100 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  const summary = analysisData?.summary;
  const healthColor = (healthData?.health_score || 0) >= 80 ? '#52c41a' : (healthData?.health_score || 0) >= 60 ? '#fa8c16' : '#ff4d4f';

  // 库存资金占用 TOP 10 柱状图
  const capitalTop10 = (analysisData?.items || [])
    .filter((i) => i.capital_occupied > 0)
    .slice(0, 10)
    .reverse();
  const capitalChartOption = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: Array<{ dataIndex: number }>) => {
        const idx = params[0]?.dataIndex;
        if (idx === undefined) return '';
        const item = capitalTop10[idx];
        if (!item) return '';
        return `${item.product_name}<br/>资金占用: ¥${formatNumber(item.capital_occupied)}<br/>库存: ${item.available_qty}件 × ¥${item.unit_cost}`;
      },
    },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `¥${(v / 10000).toFixed(0)}万` } },
    yAxis: {
      type: 'category' as const,
      data: capitalTop10.map((i) => i.product_name.length > 15 ? i.product_name.slice(0, 15) + '...' : i.product_name),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: capitalTop10.map((i) => Math.round(i.capital_occupied)),
      itemStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [
          { offset: 0, color: '#722ed1' }, { offset: 1, color: '#b37feb' },
        ] },
        borderRadius: [0, 4, 4, 0],
      },
      label: { show: true, position: 'right' as const, formatter: (p: { value: number }) => `¥${(p.value / 10000).toFixed(1)}万`, fontSize: 10 },
    }],
  };

  // 周转天数分布
  const turnoverItems = (analysisData?.items || []).filter((i) => i.turnover_days !== null);
  const turnoverBuckets = [
    { label: '< 15天', count: 0, color: '#52c41a' },
    { label: '15-30天', count: 0, color: '#73d13d' },
    { label: '30-60天', count: 0, color: '#faad14' },
    { label: '60-90天', count: 0, color: '#fa8c16' },
    { label: '> 90天', count: 0, color: '#ff4d4f' },
    { label: '无销量', count: 0, color: '#8c8c8c' },
  ];
  for (const item of analysisData?.items || []) {
    if (item.turnover_days === null) {
      turnoverBuckets[5].count++;
    } else if (item.turnover_days < 15) {
      turnoverBuckets[0].count++;
    } else if (item.turnover_days < 30) {
      turnoverBuckets[1].count++;
    } else if (item.turnover_days < 60) {
      turnoverBuckets[2].count++;
    } else if (item.turnover_days < 90) {
      turnoverBuckets[3].count++;
    } else {
      turnoverBuckets[4].count++;
    }
  }
  const turnoverChartOption = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} 个SKU ({d}%)' },
    legend: { bottom: 0, type: 'scroll' as const },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '42%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{c}个', fontSize: 11 },
      data: turnoverBuckets.map((b) => ({ name: b.label, value: b.count, itemStyle: { color: b.color } })),
    }],
  };

  // ============ 表格列定义 ============

  // ============ 表格列定义 ============

  // 概览表列（基于 analysisData.items，包含库存金额和成本信息）
  const overviewColumns = [
    {
      title: 'SKU', dataIndex: 'sku', width: 110,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.sku.localeCompare(b.sku),
    },
    {
      title: '商品名称', dataIndex: 'product_name',
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.product_name.localeCompare(b.product_name),
    },
    {
      title: '品牌', dataIndex: 'brand', width: 100,
      render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-',
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.brand || '').localeCompare(b.brand || ''),
    },
    {
      title: '仓库', dataIndex: 'warehouse', width: 90,
      render: (v: string) => <Tag>{v}</Tag>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.warehouse.localeCompare(b.warehouse),
    },
    {
      title: '可售', dataIndex: 'available_qty', width: 70,
      render: (v: number) => formatNumber(v),
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.available_qty - b.available_qty,
    },
    {
      title: '在途', dataIndex: 'inbound_qty', width: 60,
      render: (v: number) => formatNumber(v),
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.inbound_qty - b.inbound_qty,
    },
    {
      title: '有效库存', dataIndex: 'effective_qty', width: 80,
      render: (v: number) => <strong>{formatNumber(v)}</strong>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.effective_qty - b.effective_qty,
    },
    {
      title: '单位成本', dataIndex: 'unit_cost', width: 100,
      render: (v: number) => v > 0 ? <span style={{ color: '#666' }}>¥{v.toFixed(2)}</span> : <span style={{ color: '#bfbfbf' }}>无</span>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.unit_cost - b.unit_cost,
    },
    {
      title: '库存金额', dataIndex: 'capital_occupied', width: 130,
      render: (v: number) => v > 0 ? (
        <Tooltip title={`¥${v.toFixed(2)}`}>
          <span style={{ color: '#722ed1', fontWeight: 600 }}>{formatCurrency(v)}</span>
        </Tooltip>
      ) : <span style={{ color: '#bfbfbf' }}>无</span>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.capital_occupied - b.capital_occupied,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '风险等级',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const cfg = statusConfig[v] || statusConfig.healthy;
        return <Tag color={cfg.tagColor}>{cfg.label}</Tag>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.status.localeCompare(b.status),
    },
  ];

  // 周转分析列
  const turnoverColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', width: 200, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.product_name.localeCompare(b.product_name) },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-', sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.brand || '').localeCompare(b.brand || '') },
    { title: '可售库存', dataIndex: 'available_qty', width: 80, render: (v: number) => formatNumber(v), sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.available_qty - b.available_qty },
    { title: '4月累计销量', dataIndex: 'total_sold_qty', width: 95, render: (v: number) => formatNumber(v), sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.total_sold_qty - b.total_sold_qty },
    { title: '加权日均', dataIndex: 'weighted_daily_rate', width: 85, render: (v: number) => v > 0 ? v.toFixed(2) : '-', sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.weighted_daily_rate - b.weighted_daily_rate },
    {
      title: '周转天数',
      dataIndex: 'turnover_days',
      width: 100,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.turnover_days ?? 99999) - (b.turnover_days ?? 99999),
      render: (v: number | null) => {
        if (v === null) return <Tag color="default">无销量</Tag>;
        const color = v < 15 ? 'green' : v < 30 ? 'lime' : v < 60 ? 'orange' : v < 90 ? 'volcano' : 'red';
        return <Tag color={color}>{v}天</Tag>;
      },
    },
    { title: '资金占用', dataIndex: 'capital_occupied', width: 110, render: (v: number) => <span style={{ color: '#722ed1' }}>{formatCurrency(v)}</span>, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.capital_occupied - b.capital_occupied },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const cfg = statusConfig[v] || statusConfig.healthy;
        return <Tag color={cfg.tagColor}>{cfg.label}</Tag>;
      },
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.status.localeCompare(b.status),
    },
  ];

  // 滞销分析列
  const staleColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', width: 200, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.product_name.localeCompare(b.product_name) },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-', sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.brand || '').localeCompare(b.brand || '') },
    { title: '可售库存', dataIndex: 'available_qty', width: 80, render: (v: number) => formatNumber(v), sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.available_qty - b.available_qty },
    { title: '资金占用', dataIndex: 'capital_occupied', width: 110, render: (v: number) => <span style={{ color: '#ff4d4f' }}>{formatCurrency(v)}</span>, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.capital_occupied - b.capital_occupied },
    { title: '累计销量', dataIndex: 'total_sold_qty', width: 80, render: (v: number) => v > 0 ? formatNumber(v) : <Tag color="red">0</Tag>, sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => a.total_sold_qty - b.total_sold_qty },
    {
      title: '最后销售',
      dataIndex: 'last_sale_date',
      width: 110,
      render: (v: string | null) => v || <Tag color="red">从未销售</Tag>,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (a.last_sale_date || '').localeCompare(b.last_sale_date || ''),
    },
    {
      title: '滞销天数',
      dataIndex: 'stale_days',
      width: 100,
      sorter: (a: InventoryAnalysisItem, b: InventoryAnalysisItem) => (b.stale_days ?? -1) - (a.stale_days ?? -1),
      render: (v: number | null) => {
        if (v === null) return <Tag color="red">从未</Tag>;
        const color = v >= 60 ? 'red' : v >= 30 ? 'orange' : 'default';
        return <Tag color={color}>{v}天</Tag>;
      },
    },
    {
      title: '建议',
      dataIndex: 'is_stale',
      width: 120,
      render: (_: boolean, record: InventoryAnalysisItem) => {
        if (record.available_qty > 50) return <Tag color="volcano">促销清仓</Tag>;
        if (record.available_qty > 0) return <Tag color="orange">考虑清仓</Tag>;
        return <Tag color="default">无需操作</Tag>;
      },
    },
  ];

  // filteredAnalysis 和 staleItems 已在 loading 早返回之前定义（保持 hooks 顺序稳定）
  // reorderColumnDefs / handleReorderResize / reorderColumns 同样在早返回之前定义（hooks 顺序稳定）

  return (
    <div className="page-container">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Segmented
            options={brandOptions}
            value={brand}
            onChange={(v) => setBrand(v as string)}
          />
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 150 }}
            options={periods.map((p) => ({
              label: `${p.period}（¥${(p.net_revenue / 10000).toFixed(1)}万）`,
              value: p.period,
            }))}
            placeholder="选择月份"
          />
        </Space>
        <Space>
          <Input.Search
            placeholder="搜索SKU或商品名"
            allowClear
            style={{ width: 240 }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Button
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={async () => {
              setExporting(true);
              try {
                const exportParams: Record<string, string> = {};
                if (brand) exportParams.brand = brand;
                if (month) exportParams.month = month;
                const resp = await exportApi.inventory(exportParams);
                const url = window.URL.createObjectURL(resp.data as Blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Inventory_${month || 'all'}.xlsx`;
                a.click();
                window.URL.revokeObjectURL(url);
              } finally { setExporting(false); }
            }}
          >
            导出Excel
          </Button>
        </Space>
      </div>

      {/* 旺店通API库存同步状态 */}
      {wangdianStatus && (
        <Alert
          type={wangdianStatus.configured ? 'success' : 'error'}
          showIcon
          icon={<ApiOutlined />}
          style={{ marginBottom: 12 }}
          message={
            <Space size="middle" wrap>
              <span style={{ fontWeight: 600 }}>旺店通API实时同步</span>
              {wangdianStatus.configured ? (
                <Tag color="green">已配置</Tag>
              ) : (
                <Tag color="red">未配置凭证</Tag>
              )}
              {wangdianStatus.configured && (
                <>
                  <Tag color="blue">stock_query.php 无时间限制</Tag>
                  <span>本系统库存：<strong>{wangdianStatus.sales_analysis_latest_date || '—'}</strong></span>
                  {wangdianStatus.last_sync_at && (
                    <span style={{ color: '#999', fontSize: 12 }}>
                      上次同步：{new Date(wangdianStatus.last_sync_at).toLocaleString('zh-CN')}
                      {wangdianStatus.last_synced_date && `（${wangdianStatus.last_synced_date}）`}
                    </span>
                  )}
                  {wangdianStatus.last_total_from_api !== null && wangdianStatus.last_total_from_api > 0 && (
                    <Tag color="cyan">
                      上次拉取 {wangdianStatus.last_total_from_api} 条 / {wangdianStatus.last_warehouse_count} 仓库
                    </Tag>
                  )}
                  {wangdianStatus.last_auto_created !== null && wangdianStatus.last_auto_created > 0 && (
                    <Tag color="blue">自动创建 {wangdianStatus.last_auto_created} 个新品</Tag>
                  )}
                  <Button
                    type="primary"
                    size="small"
                    icon={<SyncOutlined spin={wangdianSyncing} />}
                    loading={wangdianSyncing}
                    onClick={handleSyncFromWangdian}
                  >
                    立即同步
                  </Button>
                </>
              )}
            </Space>
          }
          description={
            wangdianStatus.configured
              ? '旺店通ERP实时库存数据直连，每天凌晨01:00自动同步最近30天变动。仅保留3个核心仓库（美乐印刷/速易正品仓/速易瑞福兰仓），按SKU+仓库原地更新不累积重复记录。'
              : '请在服务器 .env 文件中配置 WANGDIAN_SID / WANGDIAN_APPKEY / WANGDIAN_APPSECRET 后重启服务'
          }
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'overview',
            label: '库存概览',
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={24} md={6}>
                    <Card title="库存健康评分">
                      <div style={{ textAlign: 'center', padding: '10px 0' }}>
                        <Progress
                          type="dashboard"
                          percent={healthData?.health_score || 0}
                          strokeColor={healthColor}
                          format={(p) => <span style={{ fontSize: 28, fontWeight: 700, color: healthColor }}>{p}</span>}
                        />
                        <p style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                          {healthData?.total_skus || 0} 个SKU
                        </p>
                      </div>
                    </Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card title="风险分布" size="small">
                      <Statistic title="缺货" value={healthData?.stockout_count || 0} valueStyle={{ color: '#ff4d4f' }} suffix="SKU" />
                      <Statistic title="低库存" value={healthData?.low_stock_count || 0} valueStyle={{ color: '#fa8c16', fontSize: 18 }} suffix="SKU" style={{ marginTop: 8 }} />
                      <Statistic title="积压" value={healthData?.overstock_count || 0} valueStyle={{ color: '#1677ff', fontSize: 18 }} suffix="SKU" style={{ marginTop: 8 }} />
                    </Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card title="资金占用" size="small">
                      <Statistic
                        title="库存总资金"
                        value={summary?.total_capital || 0}
                        precision={2}
                        prefix="¥"
                        valueStyle={{ color: '#722ed1' }}
                      />
                      <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                        平均周转: <strong style={{ color: (summary?.avg_turnover_days || 0) > 60 ? '#ff4d4f' : '#52c41a' }}>{summary?.avg_turnover_days || 0}天</strong>
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        滞销SKU: <strong style={{ color: '#8c8c8c' }}>{summary?.stale_count || 0}个</strong>
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        需补货: <strong style={{ color: '#fa8c16' }}>{summary?.reorder_count || 0}个</strong>
                      </div>
                    </Card>
                  </Col>
                  <Col xs={24} md={6}>
                    <Card title="数据周期" size="small">
                      <Statistic title="分析跨度" value={summary?.weighted_months || 4} suffix="个月" />
                      <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                        {summary?.data_start} ~ {summary?.data_end}
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        采购周期: {summary?.procurement_days || 60}天
                      </div>
                    </Card>
                  </Col>
                </Row>

                <Card title="库存资金占用 TOP 10" style={{ marginTop: 16 }}>
                  {capitalTop10.length > 0 ? (
                    <ReactECharts option={capitalChartOption} style={{ height: 320 }} />
                  ) : (
                    <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无资金占用数据（缺少单位成本）</div>
                  )}
                </Card>

                <Card
                  title={
                    <Space size="small">
                      <span>库存明细</span>
                      <Tag color="purple">{overviewSummary.skuCount} 个SKU</Tag>
                      <Tag color="cyan">{formatNumber(overviewSummary.totalQty)} 件库存</Tag>
                    </Space>
                  }
                  extra={
                    <Space size="middle">
                      <span style={{ fontSize: 13, color: '#666' }}>
                        库存总金额：
                        <strong style={{ color: '#722ed1', fontSize: 16 }}>
                          {formatCurrency(overviewSummary.totalCapital)}
                        </strong>
                        {overviewSummary.withCostCount < overviewSummary.skuCount && (
                          <Tooltip title={`${overviewSummary.skuCount - overviewSummary.withCostCount} 个SKU缺少成本，未计入金额`}>
                            <Tag color="warning" style={{ marginLeft: 6 }}>
                              {overviewSummary.skuCount - overviewSummary.withCostCount} 个无成本
                            </Tag>
                          </Tooltip>
                        )}
                      </span>
                      <Button
                        size="small"
                        icon={<ClearOutlined />}
                        onClick={resetOverviewFilters}
                        disabled={!search && warehouseFilter.length === 0 && !statusFilter && !costFilter && !amountBucket}
                      >
                        重置筛选
                      </Button>
                    </Space>
                  }
                  style={{ marginTop: 16 }}
                >
                  <Space wrap size="small" style={{ marginBottom: 12, padding: 12, background: '#fafafa', borderRadius: 6, width: '100%' }}>
                    <span style={{ color: '#999', fontSize: 12 }}>筛选：</span>
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="仓库（多选）"
                      style={{ minWidth: 180 }}
                      value={warehouseFilter}
                      onChange={setWarehouseFilter}
                      options={warehouseOptions.map((w) => ({ label: w, value: w }))}
                      maxTagCount="responsive"
                    />
                    <Select
                      allowClear
                      placeholder="风险等级"
                      style={{ width: 130 }}
                      value={statusFilter || undefined}
                      onChange={(v) => setStatusFilter(v || '')}
                      options={[
                        { label: '缺货', value: 'stockout' },
                        { label: '滞销', value: 'stale' },
                        { label: '需补货', value: 'reorder' },
                        { label: '积压', value: 'overstock' },
                        { label: '健康', value: 'healthy' },
                      ]}
                    />
                    <Segmented
                      options={[
                        { label: '全部', value: '' },
                        { label: '有成本', value: 'with' },
                        { label: '无成本', value: 'without' },
                      ]}
                      value={costFilter}
                      onChange={(v) => setCostFilter(v as string)}
                    />
                    <Segmented
                      options={[
                        { label: '金额:全部', value: '' },
                        { label: '<¥1万', value: '1w' },
                        { label: '¥1-10万', value: '10w' },
                        { label: '¥10-50万', value: '50w' },
                        { label: '>¥50万', value: '50w+' },
                      ]}
                      value={amountBucket}
                      onChange={(v) => setAmountBucket(v as string)}
                    />
                    {(warehouseFilter.length > 0 || statusFilter || costFilter || amountBucket) && (
                      <span style={{ color: '#1677ff', fontSize: 12 }}>
                        ✓ 已应用筛选条件
                      </span>
                    )}
                  </Space>
                  <Table
                    dataSource={filteredOverview}
                    columns={overviewColumns}
                    rowKey={(r) => `${r.sku}-${r.warehouse}`}
                    size="small"
                    pagination={standardPagination(20)}
                    scroll={{ x: 1200 }}
                    locale={{
                      emptyText: <Empty description="没有符合筛选条件的库存明细" />,
                    }}
                  />
                </Card>
              </>
            ),
          },
          {
            key: 'turnover',
            label: '周转分析',
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={24} md={10}>
                    <Card title="周转天数分布">
                      <ReactECharts option={turnoverChartOption} style={{ height: 300 }} />
                    </Card>
                  </Col>
                  <Col xs={24} md={14}>
                    <Card title="关键指标">
                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Statistic title="平均周转天数" value={summary?.avg_turnover_days || 0} suffix="天" valueStyle={{ color: (summary?.avg_turnover_days || 0) > 60 ? '#ff4d4f' : '#52c41a' }} />
                        </Col>
                        <Col span={12}>
                          <Statistic title="库存总资金" value={summary?.total_capital || 0} prefix="¥" precision={2} valueStyle={{ color: '#722ed1' }} />
                        </Col>
                        <Col span={12}>
                          <Statistic title="有销量SKU" value={turnoverItems.length} suffix="个" />
                        </Col>
                        <Col span={12}>
                          <Statistic title="无销量SKU" value={(summary?.total_skus || 0) - turnoverItems.length} suffix="个" valueStyle={{ color: '#8c8c8c' }} />
                        </Col>
                      </Row>
                      <div style={{ marginTop: 16, padding: 12, background: '#f6f8fa', borderRadius: 8, fontSize: 13, color: '#666' }}>
                        <strong>周转天数 = 当前可售库存 ÷ 日均销量</strong><br />
                        <span>&lt; 30天 = 周转良好 | 30-60天 = 需关注 | &gt; 60天 = 库存积压风险</span>
                      </div>
                    </Card>
                  </Col>
                </Row>

                <Card title="SKU周转明细" style={{ marginTop: 16 }}>
                  <Table
                    dataSource={filteredAnalysis}
                    columns={turnoverColumns}
                    rowKey={(r) => `${r.sku}-${r.warehouse}`}
                    size="small"
                    pagination={standardPagination(20)}
                    scroll={{ x: 800 }}
                  />
                </Card>
              </>
            ),
          },
          {
            key: 'stale',
            label: `滞销分析${staleItems.length > 0 ? ` (${staleItems.length})` : ''}`,
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="滞销SKU数" value={staleItems.length} suffix="个" valueStyle={{ color: '#8c8c8c' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="滞销资金占用" value={staleItems.reduce((s, i) => s + i.capital_occupied, 0)} prefix="¥" precision={2} valueStyle={{ color: '#ff4d4f' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="从未销售" value={staleItems.filter((i) => i.stale_days === null).length} suffix="个" valueStyle={{ color: '#ff4d4f' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="30天+未销售" value={staleItems.filter((i) => i.stale_days !== null && i.stale_days >= 30).length} suffix="个" valueStyle={{ color: '#fa8c16' }} /></Card>
                  </Col>
                </Row>
                <Card title="滞销SKU明细" style={{ marginTop: 16 }}>
                  {staleItems.length > 0 ? (
                    <Table
                      dataSource={staleItems}
                      columns={staleColumns}
                      rowKey={(r) => `${r.sku}-${r.warehouse}`}
                      size="small"
                      pagination={standardPagination(20)}
                      scroll={{ x: 800 }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', padding: 40, color: '#52c41a' }}>
                      没有滞销SKU，库存周转状况良好
                    </div>
                  )}
                </Card>
              </>
            ),
          },
          {
            key: 'reorder',
            label: `补货建议${reorderItems.length > 0 ? ` (${reorderItems.length})` : ''}`,
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={4}>
                    <Card
                      size="small"
                      hoverable
                      onClick={() => setReorderFilter('all')}
                      style={{
                        cursor: 'pointer',
                        borderColor: reorderFilter === 'all' ? '#fa8c16' : undefined,
                        background: reorderFilter === 'all' ? '#fff7e6' : undefined,
                      }}
                    >
                      <Statistic title="需补货SKU" value={reorderItems.length} suffix="个" valueStyle={{ color: '#fa8c16' }} />
                      {reorderFilter === 'all' && <div style={{ fontSize: 11, color: '#fa8c16', marginTop: 2 }}>✓ 已选中</div>}
                    </Card>
                  </Col>
                  <Col xs={12} md={4}>
                    <Card
                      size="small"
                      hoverable
                      onClick={() => setReorderFilter('urgent')}
                      style={{
                        cursor: 'pointer',
                        borderColor: reorderFilter === 'urgent' ? '#ff4d4f' : undefined,
                        background: reorderFilter === 'urgent' ? '#fff1f0' : undefined,
                      }}
                    >
                      <Statistic title="紧急缺货" value={summary?.urgent_count || 0} suffix="个" valueStyle={{ color: '#ff4d4f' }} />
                      {reorderFilter === 'urgent' && <div style={{ fontSize: 11, color: '#ff4d4f', marginTop: 2 }}>✓ 已选中</div>}
                    </Card>
                  </Col>
                  <Col xs={12} md={4}>
                    <Card
                      size="small"
                      hoverable
                      onClick={() => setReorderFilter('normal')}
                      style={{
                        cursor: 'pointer',
                        borderColor: reorderFilter === 'normal' ? '#fa8c16' : undefined,
                        background: reorderFilter === 'normal' ? '#fff7e6' : undefined,
                      }}
                    >
                      <Statistic title="常规补货" value={summary?.normal_count || 0} suffix="个" valueStyle={{ color: '#fa8c16' }} />
                      {reorderFilter === 'normal' && <div style={{ fontSize: 11, color: '#fa8c16', marginTop: 2 }}>✓ 已选中</div>}
                    </Card>
                  </Col>
                  <Col xs={12} md={4}>
                    <Card
                      size="small"
                      hoverable
                      onClick={() => { setReorderFilter('all'); setReorderSort('qty'); }}
                      style={{
                        cursor: 'pointer',
                        borderColor: reorderSort === 'qty' ? '#1677ff' : undefined,
                        background: reorderSort === 'qty' ? '#e6f4ff' : undefined,
                      }}
                    >
                      <Statistic title="补货总量" value={summary?.total_reorder_qty || 0} suffix="件" valueStyle={{ color: '#1677ff' }} />
                      {reorderSort === 'qty' && <div style={{ fontSize: 11, color: '#1677ff', marginTop: 2 }}>✓ 按补货量排序</div>}
                    </Card>
                  </Col>
                  <Col xs={12} md={4}>
                    <Card
                      size="small"
                      hoverable
                      onClick={() => { setReorderFilter('all'); setReorderSort('value'); }}
                      style={{
                        cursor: 'pointer',
                        borderColor: reorderSort === 'value' ? '#722ed1' : undefined,
                        background: reorderSort === 'value' ? '#f9f0ff' : undefined,
                      }}
                    >
                      <Statistic title="采购预算" value={summary?.total_reorder_value || 0} prefix="¥" precision={2} valueStyle={{ color: '#722ed1' }} />
                      {reorderSort === 'value' && <div style={{ fontSize: 11, color: '#722ed1', marginTop: 2 }}>✓ 按采购金额排序</div>}
                    </Card>
                  </Col>
                  <Col xs={12} md={4}>
                    <Card size="small">
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>补货引擎参数</div>
                      <div style={{ fontSize: 12, lineHeight: 1.8 }}>
                        <span>加权月数: <strong>{summary?.weighted_months || 6}</strong>（权重 {summary?.month_weights?.join('/') || '6/5/4/3/2/1'}）</span><br />
                        <span>采购周期: <strong>{summary?.procurement_days || 60}</strong>天</span><br />
                        <span>安全系数: <strong style={{ color: '#fa8c16' }}>{summary?.safety_factor_fast || 1.7}</strong>x（快消）/ <strong style={{ color: '#1677ff' }}>{summary?.safety_factor_slow || 1.3}</strong>x（慢消）</span>
                      </div>
                    </Card>
                  </Col>
                </Row>
                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                  <Col xs={24} md={12}>
                    <Card size="small" title="快消品 vs 慢消品">
                      <Row gutter={16}>
                        <Col span={12}>
                          <Statistic
                            title="快消品（周转<2月）"
                            value={summary?.fast_moving_count || 0}
                            suffix="个"
                            valueStyle={{ color: '#fa8c16' }}
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="慢消品（周转≥2月）"
                            value={summary?.slow_moving_count || 0}
                            suffix="个"
                            valueStyle={{ color: '#1677ff' }}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card size="small" title="计算公式">
                      <div style={{ fontSize: 12, lineHeight: 1.8, color: '#666' }}>
                        <strong>① 加权日均</strong> = Σ(各月日均 × 权重) / Σ权重，权重 [6,5,4,3,2,1]<br />
                        <strong>② 周转天数</strong> = 当前库存 ÷ 加权日均<br />
                        <strong>③ 安全系数</strong> = 周转&lt;60天 → 1.7x；周转≥60天 → 1.3x<br />
                        <strong>④ 安全库存</strong> = 加权日均 × 60天 × 安全系数<br />
                        <strong>⑤ 补货量</strong> = max(安全库存 + 周期需求 - 有效库存, 周期需求)<br />
                        <strong>⑥ 优先级</strong> = 供应&lt;7天→紧急；&lt;60天→常规；否则→计划
                      </div>
                    </Card>
                  </Col>
                </Row>
                <Card
                  title={
                    <Space size="small">
                      <span>补货建议明细</span>
                      <Tag color="orange">{filteredReorderItems.length} 个SKU</Tag>
                      {search && <Tag color="cyan">搜索: "{search}"</Tag>}
                      {reorderSort !== 'default' && (
                        <Tag color={reorderSort === 'qty' ? 'blue' : 'purple'}>
                          按{reorderSort === 'qty' ? '补货量' : '采购金额'}排序
                        </Tag>
                      )}
                      {reorderColumnSort && (
                        <Tag color="geekblue">
                          {reorderColumnSort.key} {reorderColumnSort.order === 'ascend' ? '↑' : '↓'}
                        </Tag>
                      )}
                      {(reorderFilter !== 'all' || reorderSort !== 'default' || search || reorderColumnSort ||
                        reorderBrandFilter.length > 0 || reorderTurnoverFilter.length > 0 ||
                        reorderTrendFilter.length > 0 || reorderPriorityFilter.length > 0 ||
                        reorderSafetyFilter.length > 0) && (
                        <Button
                          size="small"
                          type="link"
                          icon={<ClearOutlined />}
                          onClick={() => {
                            setReorderFilter('all');
                            setReorderSort('default');
                            setSearch('');
                            setReorderColumnSort(null);
                            setReorderBrandFilter([]);
                            setReorderTurnoverFilter([]);
                            setReorderTrendFilter([]);
                            setReorderPriorityFilter([]);
                            setReorderSafetyFilter([]);
                          }}
                        >
                          清除筛选/排序
                        </Button>
                      )}
                    </Space>
                  }
                  style={{ marginTop: 16 }}
                >
                  {/* 表格上方多选筛选条（用原生 div flex 而非 Space wrap，确保每个 Select 都能正常点击+展开下拉） */}
                  <div
                    style={{
                      marginBottom: 12,
                      padding: 12,
                      background: '#fafafa',
                      borderRadius: 6,
                      display: 'flex',
                      flexWrap: 'wrap',
                      alignItems: 'center',
                      gap: 8,
                      position: 'relative',
                      zIndex: 1,
                    }}
                  >
                    <span style={{ color: '#999', fontSize: 12 }}>筛选：</span>
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="品牌"
                      style={{ minWidth: 160 }}
                      value={reorderBrandFilter}
                      onChange={setReorderBrandFilter}
                      options={reorderBrandOptions.map((b) => ({ label: b, value: b }))}
                      maxTagCount="responsive"
                      popupMatchSelectWidth={false}
                      getPopupContainer={(trigger) => trigger.parentElement || document.body}
                    />
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="周转分类"
                      style={{ minWidth: 130 }}
                      value={reorderTurnoverFilter}
                      onChange={setReorderTurnoverFilter}
                      options={[
                        { label: '快消', value: 'fast' },
                        { label: '慢消', value: 'slow' },
                      ]}
                      maxTagCount="responsive"
                      popupMatchSelectWidth={false}
                      getPopupContainer={(trigger) => trigger.parentElement || document.body}
                    />
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="趋势"
                      style={{ minWidth: 130 }}
                      value={reorderTrendFilter}
                      onChange={setReorderTrendFilter}
                      options={[
                        { label: '↑ 上升', value: 'up' },
                        { label: '↓ 下降', value: 'down' },
                        { label: '→ 平稳', value: 'flat' },
                      ]}
                      maxTagCount="responsive"
                      popupMatchSelectWidth={false}
                      getPopupContainer={(trigger) => trigger.parentElement || document.body}
                    />
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="优先级"
                      style={{ minWidth: 140 }}
                      value={reorderPriorityFilter}
                      onChange={setReorderPriorityFilter}
                      options={[
                        { label: <Tag color="red" style={{ margin: 0 }}>紧急</Tag>, value: 'urgent' },
                        { label: <Tag color="orange" style={{ margin: 0 }}>常规</Tag>, value: 'normal' },
                        { label: <Tag color="blue" style={{ margin: 0 }}>计划</Tag>, value: 'planned' },
                      ]}
                      maxTagCount="responsive"
                      popupMatchSelectWidth={false}
                      getPopupContainer={(trigger) => trigger.parentElement || document.body}
                    />
                    <Select
                      mode="multiple"
                      allowClear
                      placeholder="安全系数"
                      style={{ minWidth: 130 }}
                      value={reorderSafetyFilter}
                      onChange={setReorderSafetyFilter}
                      options={[
                        { label: '1.7x（快消）', value: '1.7' },
                        { label: '1.3x（慢消）', value: '1.3' },
                      ]}
                      maxTagCount="responsive"
                      popupMatchSelectWidth={false}
                      getPopupContainer={(trigger) => trigger.parentElement || document.body}
                    />
                    {(reorderBrandFilter.length > 0 || reorderTurnoverFilter.length > 0 ||
                      reorderTrendFilter.length > 0 || reorderPriorityFilter.length > 0 ||
                      reorderSafetyFilter.length > 0) && (
                      <span style={{ color: '#1677ff', fontSize: 12 }}>✓ 多选筛选已应用</span>
                    )}
                    <span style={{ color: '#999', fontSize: 12, marginLeft: 'auto' }}>
                      提示：点击表格列头可切换排序
                    </span>
                  </div>
                  {filteredReorderItems.length > 0 ? (
                    <Table
                      dataSource={filteredReorderItems}
                      columns={reorderColumns}
                      rowKey={(r) => `${r.sku}-${r.warehouse}`}
                      size="small"
                      pagination={standardPagination(20)}
                      scroll={{ x: 1400 }}
                      components={{
                        header: { cell: ResizableHeader as never },
                      }}
                      onChange={(_pagination, _filters, sorter) => {
                        // 列头点击排序：把排序状态同步到 reorderColumnSort
                        const s = Array.isArray(sorter) ? sorter[0] : sorter;
                        if (s && s.order && s.field) {
                          setReorderColumnSort({ key: s.field as string, order: s.order });
                          setReorderSort('default'); // 列点击后清掉卡片预设
                        } else {
                          setReorderColumnSort(null);
                        }
                      }}
                    />
                  ) : reorderItems.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 40, color: '#52c41a' }}>
                      所有SKU库存充足，暂无补货需求
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                      当前筛选条件下没有数据
                      <div style={{ marginTop: 8 }}>
                        <Button size="small" onClick={() => setReorderFilter('all')}>查看全部补货项</Button>
                      </div>
                    </div>
                  )}
                </Card>
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
