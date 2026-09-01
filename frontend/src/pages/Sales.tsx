import { useEffect, useState, useCallback, useMemo } from 'react';
import { Row, Col, Card, Table, Tag, DatePicker, Select, Button, Space, Tabs, Segmented, Empty, Spin, Statistic } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { salesApi, exportApi } from '../api';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import type { StoreSales, ProductSales, PlatformSales, CategorySales, StoreOption } from '../types';
import { formatCurrency, formatNumber, formatPercent, formatQty } from '../utils/format';
import dayjs from 'dayjs';

interface MonthlyCompareItem {
  month: string;
  revenue: number;
  cost: number;
  profit: number;
  gross_margin_pct: number;
  ship_amount: number;
  return_amount: number;
  return_rate: number;
  ship_qty: number;
  return_qty: number;
  net_qty: number;
  commission_cost: number;
  order_count: number;
  revenue_mom: number | null;
  profit_mom: number | null;
  order_count_mom: number | null;
}

const { RangePicker } = DatePicker;

const brandOptions = [
  { label: '全部品牌', value: '' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

export default function Sales() {
  const [brand, setBrand] = useState<string>('');
  const { periods, month, setMonth } = usePeriods();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [selectedStore, setSelectedStore] = useState<string | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('store');

  const [stores, setStores] = useState<StoreSales[]>([]);
  const [products, setProducts] = useState<ProductSales[]>([]);
  const [platforms, setPlatforms] = useState<PlatformSales[]>([]);
  const [categories, setCategories] = useState<CategorySales[]>([]);
  const [storeOptions, setStoreOptions] = useState<StoreOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // 月度对比
  const [compareMonths, setCompareMonths] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<MonthlyCompareItem[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);

  const params: Record<string, string> = {};
  if (brand) params.brand = brand;
  if (month) params.month = month;
  if (dateRange) {
    params.start_date = dateRange[0].format('YYYY-MM-DD');
    params.end_date = dateRange[1].format('YYYY-MM-DD');
  }
  if (selectedStore) params.store_id = selectedStore;

  const loadData = useCallback(() => {
    if (!month) return;
    setLoading(true);
    Promise.all([
      salesApi.byStore({ ...params, limit: 100 }),
      salesApi.byProduct({ ...params, limit: 100 }),
      salesApi.byPlatform(params),
      salesApi.byCategory(params),
    ])
      .then(([st, pr, pf, cat]) => {
        setStores(st.data.data.stores);
        setProducts(pr.data.data.products);
        setPlatforms(pf.data.data.platforms);
        setCategories(cat.data.data.categories);
      })
      .finally(() => setLoading(false));
  }, [brand, month, dateRange, selectedStore]);

  useEffect(() => {
    salesApi.stores(brand ? { brand } : {}).then((res) => setStoreOptions(res.data.data));
  }, [brand]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 初次加载 periods 后，默认选中近 4 个月作为对比基准
  useEffect(() => {
    if (periods.length > 0 && compareMonths.length === 0) {
      const recent = periods.slice(0, 4).map((p) => p.period).reverse(); // 升序
      setCompareMonths(recent);
    }
  }, [periods, compareMonths.length]);

  // 加载月度对比数据
  const loadCompareData = useCallback(() => {
    if (compareMonths.length === 0) {
      setCompareData([]);
      return;
    }
    setCompareLoading(true);
    const monthsParam = [...compareMonths].sort().join(',');
    const compareParams: Record<string, string> = { months: monthsParam };
    if (brand) compareParams.brand = brand;
    salesApi.monthlyCompare(compareParams)
      .then((res) => setCompareData(res.data.data.comparison || []))
      .finally(() => setCompareLoading(false));
  }, [compareMonths, brand]);

  useEffect(() => {
    loadCompareData();
  }, [loadCompareData]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const exportParams: Record<string, string> = {};
      if (brand) exportParams.brand = brand;
      if (month) exportParams.month = month;
      const resp = await exportApi.sales(exportParams);
      const url = window.URL.createObjectURL(resp.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Sales_${month || 'all'}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } finally { setExporting(false); }
  };

  const platformOption = {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'shadow' as const } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category' as const, data: platforms.map((p) => p.platform), axisLabel: { fontSize: 11 } },
    yAxis: [
      { type: 'value' as const, name: '销售额', axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` } },
      { type: 'value' as const, name: '毛利率(%)', max: 100 },
    ],
    series: [
      {
        name: '销售额',
        type: 'bar',
        data: platforms.map((p) => Math.round(p.total_revenue)),
        itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '毛利率',
        type: 'line',
        yAxisIndex: 1,
        data: platforms.map((p) => Number(p.gross_margin_pct.toFixed(2))),
        itemStyle: { color: '#52c41a' },
        lineStyle: { width: 2 },
      },
    ],
  };

  // 月度对比图表（双 Y 轴：销售额/毛利柱 + 毛利率折线）
  const compareOption = useMemo(() => {
    if (compareData.length === 0) return null;
    const months = compareData.map((c) => c.month);
    return {
      tooltip: { trigger: 'axis' as const, axisPointer: { type: 'cross' as const } },
      legend: { top: 0, data: ['销售额', '毛利', '毛利率(%)'] },
      grid: { left: '3%', right: '5%', bottom: '5%', top: 50, containLabel: true },
      xAxis: { type: 'category' as const, data: months, axisLabel: { fontSize: 12 } },
      yAxis: [
        { type: 'value' as const, name: '金额(元)', axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` } },
        { type: 'value' as const, name: '毛利率(%)', max: 100, axisLabel: { formatter: (v: number) => `${v}%` } },
      ],
      series: [
        {
          name: '销售额',
          type: 'bar',
          data: compareData.map((c) => Math.round(c.revenue)),
          itemStyle: { color: '#1677ff', borderRadius: [4, 4, 0, 0] },
          barWidth: 30,
        },
        {
          name: '毛利',
          type: 'bar',
          data: compareData.map((c) => Math.round(c.profit)),
          itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] },
          barWidth: 30,
        },
        {
          name: '毛利率(%)',
          type: 'line',
          yAxisIndex: 1,
          data: compareData.map((c) => Number(c.gross_margin_pct.toFixed(2))),
          itemStyle: { color: '#fa8c16' },
          lineStyle: { width: 3 },
          symbol: 'circle',
          symbolSize: 8,
        },
      ],
    };
  }, [compareData]);

  // 月度对比表（环比涨跌用红涨绿跌）
  const renderMom = (v: number | null) => {
    if (v === null || v === undefined) return <span style={{ color: '#ccc' }}>-</span>;
    const isUp = v > 0;
    const isFlat = v === 0;
    return (
      <span style={{ color: isFlat ? '#999' : isUp ? '#cf1322' : '#3f8600', fontWeight: 600 }}>
        {isUp ? '↑' : isFlat ? '→' : '↓'} {Math.abs(v).toFixed(1)}%
      </span>
    );
  };

  const compareColumns = [
    { title: '月份', dataIndex: 'month', width: 100, fixed: 'left' as const, render: (v: string) => <Tag color="blue">{v}</Tag>, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.month.localeCompare(b.month) },
    {
      title: '销售额',
      dataIndex: 'revenue',
      width: 130,
      render: (v: number) => <strong style={{ color: '#1677ff' }}>{formatCurrency(v)}</strong>,
      sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.revenue - b.revenue,
    },
    { title: '销售环比', dataIndex: 'revenue_mom', width: 110, render: renderMom, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => (a.revenue_mom ?? -999) - (b.revenue_mom ?? -999) },
    { title: '毛利', dataIndex: 'profit', width: 120, render: (v: number) => <strong style={{ color: '#52c41a' }}>{formatCurrency(v)}</strong>, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.profit - b.profit },
    { title: '毛利环比', dataIndex: 'profit_mom', width: 110, render: renderMom, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => (a.profit_mom ?? -999) - (b.profit_mom ?? -999) },
    { title: '成本', dataIndex: 'cost', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.cost - b.cost },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{v.toFixed(1)}%</Tag>,
      sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.gross_margin_pct - b.gross_margin_pct,
    },
    { title: '订单数', dataIndex: 'order_count', width: 90, render: (v: number) => formatNumber(v), sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.order_count - b.order_count },
    { title: '订单环比', dataIndex: 'order_count_mom', width: 110, render: renderMom, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => (a.order_count_mom ?? -999) - (b.order_count_mom ?? -999) },
    { title: '实际销量', dataIndex: 'net_qty', width: 90, render: (v: number) => formatQty(v), sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.net_qty - b.net_qty },
    { title: '退货率', dataIndex: 'return_rate', width: 90, render: (v: number) => <Tag color={v >= 15 ? 'red' : v >= 8 ? 'orange' : 'green'}>{v.toFixed(1)}%</Tag>, sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.return_rate - b.return_rate },
    { title: '退货金额', dataIndex: 'return_amount', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: MonthlyCompareItem, b: MonthlyCompareItem) => a.return_amount - b.return_amount },
  ];

  // 汇总行
  const compareSummary = useMemo(() => {
    if (compareData.length === 0) return null;
    const totalRevenue = compareData.reduce((s, c) => s + c.revenue, 0);
    const totalProfit = compareData.reduce((s, c) => s + c.profit, 0);
    const totalCost = compareData.reduce((s, c) => s + c.cost, 0);
    const totalOrders = compareData.reduce((s, c) => s + c.order_count, 0);
    const totalReturn = compareData.reduce((s, c) => s + c.return_amount, 0);
    const totalShip = compareData.reduce((s, c) => s + c.ship_amount, 0);
    const totalQty = compareData.reduce((s, c) => s + c.net_qty, 0);
    return {
      months: compareData.length,
      totalRevenue,
      totalProfit,
      totalCost,
      totalOrders,
      totalReturn,
      totalShip,
      totalQty,
      avgMargin: totalRevenue > 0 ? (totalProfit / totalRevenue * 100) : 0,
      avgReturnRate: totalShip > 0 ? (totalReturn / totalShip * 100) : 0,
      avgOrder: totalOrders > 0 ? (totalRevenue / totalOrders) : 0,
    };
  }, [compareData]);

  const categoryOption = {
    tooltip: { trigger: 'item' as const },
    legend: { bottom: 0, type: 'scroll' as const },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      center: ['50%', '45%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      data: categories.filter((c) => c.total_revenue > 0).map((c) => ({
        name: c.category,
        value: Math.round(c.total_revenue),
      })),
    }],
  };

  const storeColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: '店铺名称', dataIndex: 'store_name', ellipsis: true, sorter: (a: StoreSales, b: StoreSales) => a.store_name.localeCompare(b.store_name) },
    { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag>, filters: [...new Set(stores.map(s => s.platform))].map(p => ({ text: p, value: p })), onFilter: (v: string | number | boolean, r: StoreSales) => r.platform === v },
    { title: '订单数', dataIndex: 'order_count', width: 80, render: (v: number) => formatNumber(v), sorter: (a: StoreSales, b: StoreSales) => a.order_count - b.order_count },
    { title: '销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.total_revenue - b.total_revenue, defaultSortOrder: 'descend' as const },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.gross_profit - b.gross_profit },
    { title: '折扣', dataIndex: 'total_discount', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.total_discount - b.total_discount },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: StoreSales, b: StoreSales) => a.gross_margin_pct - b.gross_margin_pct,
    },
  ];

  const productColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: 'SKU', dataIndex: 'sku', width: 120, sorter: (a: ProductSales, b: ProductSales) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true, sorter: (a: ProductSales, b: ProductSales) => a.product_name.localeCompare(b.product_name) },
    { title: '分类', dataIndex: 'category', width: 100, render: (v: string | null) => v || '-', filters: [...new Set(products.map(p => p.category).filter(Boolean))].map(c => ({ text: c, value: c })), onFilter: (v: string | number | boolean, r: ProductSales) => r.category === v },
    { title: '销量', dataIndex: 'total_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: ProductSales, b: ProductSales) => a.total_qty - b.total_qty },
    { title: '销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ProductSales, b: ProductSales) => a.total_revenue - b.total_revenue, defaultSortOrder: 'descend' as const },
    { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: ProductSales, b: ProductSales) => a.total_cost - b.total_cost },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ProductSales, b: ProductSales) => a.gross_profit - b.gross_profit },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: ProductSales, b: ProductSales) => a.gross_margin_pct - b.gross_margin_pct,
    },
  ];

  return (
    <div className="page-container">
      {/* 筛选器 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Segmented
            options={brandOptions}
            value={brand}
            onChange={(v) => { setBrand(v as string); setSelectedStore(undefined); }}
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
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            placeholder={['开始日期', '结束日期']}
          />
          <Select
            allowClear
            placeholder="选择店铺"
            style={{ width: 200 }}
            value={selectedStore}
            onChange={(v) => setSelectedStore(v)}
            options={storeOptions.map((s) => ({ label: s.store_name, value: s.id }))}
            showSearch
            optionFilterProp="label"
          />
          <Button onClick={loadData} loading={loading}>刷新</Button>
          <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>导出Excel</Button>
        </Space>
      </Card>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'store',
            label: '店铺排名',
            children: (
              <Card>
                <Table
                  dataSource={stores}
                  columns={storeColumns}
                  rowKey="store_id"
                  loading={loading}
                  size="small"
                  pagination={standardPagination(20)}
                  scroll={{ x: 800 }}
                />
              </Card>
            ),
          },
          {
            key: 'product',
            label: '商品排名',
            children: (
              <Card>
                <Table
                  dataSource={products}
                  columns={productColumns}
                  rowKey="product_id"
                  loading={loading}
                  size="small"
                  pagination={standardPagination(20)}
                  scroll={{ x: 900 }}
                />
              </Card>
            ),
          },
          {
            key: 'platform',
            label: '平台分析',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={14}>
                  <Card title="各平台销售额与毛利率">
                    <ReactECharts option={platformOption} style={{ height: 380 }} />
                  </Card>
                </Col>
                <Col xs={24} lg={10}>
                  <Card title="平台明细">
                    <Table
                      dataSource={platforms}
                      columns={[
                        { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag> },
                        { title: '店铺数', dataIndex: 'store_count', width: 70, sorter: (a: PlatformSales, b: PlatformSales) => a.store_count - b.store_count },
                        { title: '订单数', dataIndex: 'order_count', width: 80, render: (v: number) => formatNumber(v), sorter: (a: PlatformSales, b: PlatformSales) => a.order_count - b.order_count },
                        { title: '销售额', dataIndex: 'total_revenue', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: PlatformSales, b: PlatformSales) => a.total_revenue - b.total_revenue },
                        { title: '毛利率', dataIndex: 'gross_margin_pct', width: 80, render: (v: number) => formatPercent(v), sorter: (a: PlatformSales, b: PlatformSales) => a.gross_margin_pct - b.gross_margin_pct },
                      ]}
                      rowKey="platform"
                      size="small"
                      pagination={standardPagination(10)}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'category',
            label: '分类分析',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={10}>
                  <Card title="分类销售占比">
                    <ReactECharts option={categoryOption} style={{ height: 380 }} />
                  </Card>
                </Col>
                <Col xs={24} lg={14}>
                  <Card title="分类明细">
                    <Table
                      dataSource={categories}
                      columns={[
                        { title: '分类', dataIndex: 'category', width: 120, sorter: (a: CategorySales, b: CategorySales) => a.category.localeCompare(b.category) },
                        { title: 'SKU数', dataIndex: 'sku_count', width: 70, sorter: (a: CategorySales, b: CategorySales) => a.sku_count - b.sku_count },
                        { title: '销量', dataIndex: 'total_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: CategorySales, b: CategorySales) => a.total_qty - b.total_qty },
                        { title: '销售额', dataIndex: 'total_revenue', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: CategorySales, b: CategorySales) => a.total_revenue - b.total_revenue },
                        { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: CategorySales, b: CategorySales) => a.total_cost - b.total_cost },
                        { title: '毛利', dataIndex: 'gross_profit', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: CategorySales, b: CategorySales) => a.gross_profit - b.gross_profit },
                        { title: '毛利率', dataIndex: 'gross_margin_pct', width: 80, render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>, sorter: (a: CategorySales, b: CategorySales) => a.gross_margin_pct - b.gross_margin_pct },
                      ]}
                      rowKey="category"
                      size="small"
                      pagination={standardPagination(10)}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'compare',
            label: '月度对比',
            children: (
              <Spin spinning={compareLoading}>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap align="center">
                    <span style={{ color: '#666' }}>选择对比月份（可多选）：</span>
                    <Select
                      mode="multiple"
                      value={compareMonths}
                      onChange={setCompareMonths}
                      style={{ minWidth: 320, maxWidth: 600 }}
                      maxTagCount="responsive"
                      placeholder="选择月份"
                      options={periods.map((p) => ({
                        label: `${p.period}（¥${(p.net_revenue / 10000).toFixed(1)}万）`,
                        value: p.period,
                      }))}
                    />
                    <Button onClick={loadCompareData} loading={compareLoading}>刷新</Button>
                    <span style={{ color: '#999', fontSize: 12 }}>
                      当前品牌：<Tag color="cyan">{brand || '全部'}</Tag>，已选 <strong style={{ color: '#1677ff' }}>{compareMonths.length}</strong> 个月
                    </span>
                  </Space>
                </Card>

                {compareData.length === 0 ? (
                  <Card><Empty description={compareMonths.length === 0 ? '请选择至少 1 个月' : '所选月份暂无销售数据'} /></Card>
                ) : (
                  <>
                    {compareSummary && (
                      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                        <Col xs={12} md={4}>
                          <Card size="small"><Statistic title="对比月份" value={compareSummary.months} suffix="个月" valueStyle={{ color: '#1677ff' }} /></Card>
                        </Col>
                        <Col xs={12} md={5}>
                          <Card size="small"><Statistic title="累计销售额" value={compareSummary.totalRevenue} prefix="¥" precision={0} valueStyle={{ color: '#1677ff' }} /></Card>
                        </Col>
                        <Col xs={12} md={5}>
                          <Card size="small"><Statistic title="累计毛利" value={compareSummary.totalProfit} prefix="¥" precision={0} valueStyle={{ color: '#52c41a' }} /></Card>
                        </Col>
                        <Col xs={12} md={5}>
                          <Card size="small"><Statistic title="平均毛利率" value={compareSummary.avgMargin} suffix="%" precision={1} valueStyle={{ color: '#fa8c16' }} /></Card>
                        </Col>
                        <Col xs={12} md={5}>
                          <Card size="small"><Statistic title="累计订单" value={compareSummary.totalOrders} suffix="单" valueStyle={{ color: '#722ed1' }} /></Card>
                        </Col>
                      </Row>
                    )}

                    {compareOption && (
                      <Card title="销售趋势" style={{ marginBottom: 16 }}>
                        <ReactECharts option={compareOption} style={{ height: 380 }} />
                      </Card>
                    )}

                    <Card title="月度对比明细">
                      <Table
                        dataSource={compareData}
                        columns={compareColumns}
                        rowKey="month"
                      size="small"
                      pagination={standardPagination(20)}
                      scroll={{ x: 1300 }}
                        summary={(rows) => {
                          if (!compareSummary) return null;
                          return (
                            <Table.Summary fixed>
                              <Table.Summary.Row style={{ background: '#fafafa', fontWeight: 600 }}>
                                <Table.Summary.Cell index={0}><Tag color="purple">合计/平均</Tag></Table.Summary.Cell>
                                <Table.Summary.Cell index={1}>{formatCurrency(compareSummary.totalRevenue)}</Table.Summary.Cell>
                                <Table.Summary.Cell index={2}>-</Table.Summary.Cell>
                                <Table.Summary.Cell index={3}>{formatCurrency(compareSummary.totalProfit)}</Table.Summary.Cell>
                                <Table.Summary.Cell index={4}>-</Table.Summary.Cell>
                                <Table.Summary.Cell index={5}>{formatCurrency(compareSummary.totalCost)}</Table.Summary.Cell>
                                <Table.Summary.Cell index={6}>
                                  <Tag color="orange">{compareSummary.avgMargin.toFixed(1)}%</Tag>
                                </Table.Summary.Cell>
                                <Table.Summary.Cell index={7}>{formatNumber(compareSummary.totalOrders)}</Table.Summary.Cell>
                                <Table.Summary.Cell index={8}>-</Table.Summary.Cell>
                                <Table.Summary.Cell index={9}>{formatQty(compareSummary.totalQty)}</Table.Summary.Cell>
                                <Table.Summary.Cell index={10}>
                                  <Tag color={compareSummary.avgReturnRate >= 15 ? 'red' : compareSummary.avgReturnRate >= 8 ? 'orange' : 'green'}>
                                    {compareSummary.avgReturnRate.toFixed(1)}%
                                  </Tag>
                                </Table.Summary.Cell>
                                <Table.Summary.Cell index={11}>{formatCurrency(compareSummary.totalReturn)}</Table.Summary.Cell>
                              </Table.Summary.Row>
                            </Table.Summary>
                          );
                        }}
                      />
                    </Card>
                  </>
                )}
              </Spin>
            ),
          },
        ]}
      />
    </div>
  );
}
