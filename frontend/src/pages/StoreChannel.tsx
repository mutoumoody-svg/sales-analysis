import { useEffect, useState, useCallback, useMemo } from 'react';
import { Row, Col, Card, Table, Tag, Select, Button, Space, Tabs, Statistic, Input } from 'antd';
import ReactECharts from 'echarts-for-react';
import { salesApi } from '../api';
import type { ColumnsType } from 'antd/es/table';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import type {
  StoreSales,
  StoreProductDetail,
  StoreProductSummary,
  StoreMonthlyData,
  ChannelSales,
  CrossSales,
  StoreOption,
} from '../types';
import { formatCurrency, formatCurrencyShort, formatPercent, formatQty } from '../utils/format';

const brandOptions = [
  { label: '全部品牌', value: '' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

const platformColors: Record<string, string> = {
  '天猫': '#ff5000',
  '京东': '#e1251b',
  '抖音': '#000000',
  '小红书': '#ff2442',
  '拼多多': '#e02e24',
  '微信': '#07c160',
  '网易严选': '#cf0000',
};

function getPlatformColor(platform: string): string {
  return platformColors[platform] || '#8c8c8c';
}

export default function StoreChannel() {
  const [brand, setBrand] = useState<string>('');
  const { periods, month, setMonth } = usePeriods();
  const [activeTab, setActiveTab] = useState('overview');

  // Tab1: store overview
  const [stores, setStores] = useState<StoreSales[]>([]);
  // Tab2: store products
  const [storeOptions, setStoreOptions] = useState<StoreOption[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | undefined>(undefined);
  const [storeProducts, setStoreProducts] = useState<StoreProductDetail[]>([]);
  const [storeProductSummary, setStoreProductSummary] = useState<StoreProductSummary | null>(null);
  const [productSearch, setProductSearch] = useState('');
  // Tab3: channel
  const [channels, setChannels] = useState<ChannelSales[]>([]);
  const [crossData, setCrossData] = useState<CrossSales[]>([]);
  // Tab4: monthly
  const [monthlyStores, setMonthlyStores] = useState<StoreMonthlyData[]>([]);
  const [monthlyPeriods, setMonthlyPeriods] = useState<string[]>([]);
  const [monthlyMetric, setMonthlyMetric] = useState<'revenue' | 'profit'>('revenue');
  const [monthlyTopN, setMonthlyTopN] = useState(10);

  const [loading, setLoading] = useState(false);
  const [productLoading, setProductLoading] = useState(false);
  const [monthlyLoading, setMonthlyLoading] = useState(false);

  const params = useMemo(() => {
    const value: Record<string, string> = {};
    if (brand) value.brand = brand;
    if (month) value.month = month;
    return value;
  }, [brand, month]);

  // ---- Load store list + overview + channel data ----
  const loadOverviewData = useCallback(() => {
    if (!month) return;
    setLoading(true);
    Promise.all([
      salesApi.byStore({ ...params, limit: 100 }),
      salesApi.byChannel(params),
    ])
      .then(([st, ch]) => {
        setStores(st.data.data.stores);
        setChannels(ch.data.data.channels);
        setCrossData(ch.data.data.cross);
      })
      .finally(() => setLoading(false));
  }, [month, params]);

  // ---- Load store options ----
  useEffect(() => {
    salesApi.stores(brand ? { brand } : {}).then((res) => {
      setStoreOptions(res.data.data);
    });
  }, [brand]);

  // ---- Load overview when month or brand changes ----
  useEffect(() => {
    loadOverviewData();
  }, [loadOverviewData]);

  // ---- Load store products when store or month changes ----
  const loadStoreProducts = useCallback(() => {
    if (!selectedStoreId || !month) return;
    setProductLoading(true);
    const p: Record<string, string> = { store_id: selectedStoreId, ...params };
    salesApi
      .storeProducts(p)
      .then((res) => {
        setStoreProducts(res.data.data.products);
        setStoreProductSummary(res.data.data.summary);
      })
      .finally(() => setProductLoading(false));
  }, [selectedStoreId, month, params]);

  useEffect(() => {
    loadStoreProducts();
  }, [loadStoreProducts]);

  // ---- Load monthly data (no month filter, all periods) ----
  const loadMonthlyData = useCallback(() => {
    setMonthlyLoading(true);
    const p: Record<string, string> = {};
    if (brand) p.brand = brand;
    salesApi
      .storeMonthly(p)
      .then((res) => {
        setMonthlyStores(res.data.data.stores);
        setMonthlyPeriods(res.data.data.periods);
      })
      .finally(() => setMonthlyLoading(false));
  }, [brand]);

  useEffect(() => {
    loadMonthlyData();
  }, [loadMonthlyData]);

  // ---- Auto-select first store when options load ----
  useEffect(() => {
    if (storeOptions.length > 0 && !selectedStoreId) {
      setSelectedStoreId(storeOptions[0].id);
    }
  }, [storeOptions, selectedStoreId]);

  // ---- Filtered products for Tab2 search ----
  const filteredProducts = useMemo(() => {
    if (!productSearch) return storeProducts;
    const q = productSearch.toLowerCase();
    return storeProducts.filter(
      (p) =>
        p.sku?.toLowerCase().includes(q) ||
        p.product_name?.toLowerCase().includes(q) ||
        p.category?.toLowerCase().includes(q)
    );
  }, [storeProducts, productSearch]);

  // ============================
  // Tab1: 店铺总览 - chart option
  // ============================
  const overviewChartOption = useMemo(() => {
    const top10 = stores.slice(0, 15);
    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
      },
      legend: { data: ['销售额', '利润'], top: 0 },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'value' as const,
        axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` },
      },
      yAxis: {
        type: 'category' as const,
        data: top10.map((s) => s.store_name).reverse(),
        axisLabel: { fontSize: 11, width: 120, overflow: 'truncate' as const },
      },
      series: [
        {
          name: '销售额',
          type: 'bar',
          data: top10.map((s) => Math.round(s.total_revenue)).reverse(),
          itemStyle: { color: '#1677ff', borderRadius: [0, 4, 4, 0] },
        },
        {
          name: '利润',
          type: 'bar',
          data: top10.map((s) => Math.round(s.gross_profit)).reverse(),
          itemStyle: { color: '#52c41a', borderRadius: [0, 4, 4, 0] },
        },
      ],
    };
  }, [stores]);

  // ============================
  // Tab3: channel chart option
  // ============================
  const channelChartOption = useMemo(() => {
    return {
      tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0, type: 'scroll' as const },
      series: [
        {
          type: 'pie',
          radius: ['35%', '65%'],
          center: ['50%', '45%'],
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: '{b}\n{d}%', fontSize: 11 },
          data: channels
            .filter((c) => c.total_revenue > 0)
            .map((c) => ({
              name: c.channel,
              value: Math.round(c.total_revenue),
            })),
        },
      ],
    };
  }, [channels]);

  // ---- Cross heatmap data ----
  const crossMatrix = useMemo(() => {
    const platforms = [...new Set(crossData.map((c) => c.platform))];
    const channelsList = [...new Set(crossData.map((c) => c.channel))];
    const matrix: number[][] = [];
    const maxVal = Math.max(...crossData.map((c) => c.revenue), 1);

    for (const ch of channelsList) {
      const row: number[] = [];
      for (const pf of platforms) {
        const item = crossData.find((c) => c.channel === ch && c.platform === pf);
        row.push(item ? Math.round((item.revenue / maxVal) * 100) : 0);
      }
      matrix.push(row);
    }
    return { platforms, channelsList, matrix, maxVal };
  }, [crossData]);

  const crossHeatmapOption = useMemo(() => {
    const data: [number, number, number][] = [];
    for (let i = 0; i < crossMatrix.channelsList.length; i++) {
      for (let j = 0; j < crossMatrix.platforms.length; j++) {
        const item = crossData.find(
          (c) => c.channel === crossMatrix.channelsList[i] && c.platform === crossMatrix.platforms[j]
        );
        if (item) {
          data.push([j, i, Math.round(item.revenue)]);
        }
      }
    }
    return {
      tooltip: {
        position: 'top' as const,
        formatter: (params: { value: [number, number, number] }) => {
          const [pi, ci, val] = params.value;
          return `${crossMatrix.platforms[pi]} × ${crossMatrix.channelsList[ci]}<br/>销售额: ¥${val.toLocaleString()}`;
        },
      },
      grid: { left: '15%', right: '10%', top: '10%', bottom: '15%' },
      xAxis: {
        type: 'category' as const,
        data: crossMatrix.platforms,
        axisLabel: { fontSize: 11, rotate: 30 },
        splitArea: { show: true },
      },
      yAxis: {
        type: 'category' as const,
        data: crossMatrix.channelsList,
        axisLabel: { fontSize: 11 },
        splitArea: { show: true },
      },
      visualMap: {
        min: 0,
        max: Math.max(...data.map((d) => d[2]), 1),
        calculable: true,
        orient: 'horizontal' as const,
        left: 'center',
        bottom: 0,
        inRange: { color: ['#f0f5ff', '#1677ff', '#0050b3'] },
      },
      series: [
        {
          type: 'heatmap',
          data,
          label: {
            show: true,
            formatter: (params: { value: [number, number, number] }) => {
              const val = params.value[2];
              if (val === 0) return '';
              if (val >= 10000) return `${(val / 10000).toFixed(1)}万`;
              return `${val}`;
            },
            fontSize: 10,
          },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
        },
      ],
    };
  }, [crossMatrix, crossData]);

  // ============================
  // Tab4: monthly trend chart
  // ============================
  const monthlyChartOption = useMemo(() => {
    const topStores = monthlyStores.slice(0, monthlyTopN);
    const colorPool = [
      '#1677ff', '#52c41a', '#ff7a45', '#eb2f96', '#722ed1',
      '#13c2c2', '#faad14', '#a0d911', '#2f54eb', '#f5222d',
      '#fa8c16', '#08979c', '#cf1322', '#5b8c00', '#0958d9',
    ];
    return {
      tooltip: {
        trigger: 'axis' as const,
        formatter: (params: Array<{ seriesName: string; value: number; axisValue: string }>) => {
          let html = `<b>${params[0]?.axisValue}</b><br/>`;
          const sorted = [...params].sort((a, b) => b.value - a.value);
          for (const p of sorted) {
            html += `${p.seriesName}: ${formatCurrencyShort(p.value)}<br/>`;
          }
          return html;
        },
      },
      legend: {
        type: 'scroll' as const,
        bottom: 0,
        textStyle: { fontSize: 11 },
      },
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
      xAxis: {
        type: 'category' as const,
        data: monthlyPeriods,
        axisLabel: { fontSize: 12 },
      },
      yAxis: {
        type: 'value' as const,
        name: monthlyMetric === 'revenue' ? '销售额' : '利润',
        axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` },
      },
      series: topStores.map((s, idx) => ({
        name: s.store_name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2 },
        itemStyle: { color: colorPool[idx % colorPool.length] },
        data: monthlyPeriods.map((p) => {
          const m = s.months[p];
          return m ? Math.round(m[monthlyMetric]) : 0;
        }),
      })),
    };
  }, [monthlyStores, monthlyPeriods, monthlyMetric, monthlyTopN]);

  // ============================
  // Table columns
  // ============================
  const storeColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: '店铺名称', dataIndex: 'store_name', ellipsis: true, sorter: (a: StoreSales, b: StoreSales) => a.store_name.localeCompare(b.store_name) },
    {
      title: '平台',
      dataIndex: 'platform',
      width: 90,
      render: (v: string) => <Tag color={getPlatformColor(v)} style={{ color: '#fff' }}>{v}</Tag>,
      filters: [...new Set(stores.map(s => s.platform))].map(p => ({ text: p, value: p })),
      onFilter: (v: string | number | boolean, r: StoreSales) => r.platform === v,
    },
    { title: '渠道', dataIndex: 'channel', width: 100, render: (v: string | null) => v || '-', filters: [...new Set(stores.map(s => s.channel).filter(Boolean))].map(c => ({ text: c!, value: c! })), onFilter: (v: string | number | boolean, r: StoreSales) => r.channel === v },
    { title: '销量', dataIndex: 'net_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: StoreSales, b: StoreSales) => a.net_qty - b.net_qty },
    {
      title: '销售额',
      dataIndex: 'total_revenue',
      width: 120,
      render: (v: number) => formatCurrency(v),
      sorter: (a: StoreSales, b: StoreSales) => a.total_revenue - b.total_revenue,
      defaultSortOrder: 'descend' as const,
    },
    { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.total_cost - b.total_cost },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.gross_profit - b.gross_profit },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 60 ? 'green' : v >= 30 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: StoreSales, b: StoreSales) => a.gross_margin_pct - b.gross_margin_pct,
    },
    {
      title: '退货率',
      dataIndex: 'return_rate',
      width: 80,
      render: (v: number) => <span style={{ color: v > 10 ? '#ff4d4f' : '#666' }}>{formatPercent(v)}</span>,
      sorter: (a: StoreSales, b: StoreSales) => a.return_rate - b.return_rate,
    },
  ];

  const productDetailColumns = [
    { title: '排名', width: 55, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: 'SKU', dataIndex: 'sku', width: 120, sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true, sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.product_name.localeCompare(b.product_name) },
    { title: '分类', dataIndex: 'category', width: 100, render: (v: string | null) => v || '-', filters: [...new Set(storeProducts.map(p => p.category).filter(Boolean))].map(c => ({ text: c!, value: c! })), onFilter: (v: string | number | boolean, r: StoreProductDetail) => r.category === v },
    { title: '品牌', dataIndex: 'brand', width: 100, render: (v: string | null) => v || '-', filters: [...new Set(storeProducts.map(p => p.brand).filter(Boolean))].map(b => ({ text: b!, value: b! })), onFilter: (v: string | number | boolean, r: StoreProductDetail) => r.brand === v },
    { title: '发货量', dataIndex: 'ship_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.ship_qty - b.ship_qty },
    { title: '退货量', dataIndex: 'return_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.return_qty - b.return_qty },
    { title: '实际销量', dataIndex: 'net_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.net_qty - b.net_qty },
    { title: '销售额', dataIndex: 'net_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.net_revenue - b.net_revenue, defaultSortOrder: 'descend' as const },
    { title: '成本', dataIndex: 'net_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.net_cost - b.net_cost },
    { title: '佣金', dataIndex: 'commission_cost', width: 90, render: (v: number) => formatCurrency(v), sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.commission_cost - b.commission_cost },
    { title: '毛利', dataIndex: 'net_profit', width: 110, render: (v: number) => <span style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>{formatCurrency(v)}</span>, sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.net_profit - b.net_profit },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 85,
      render: (v: number) => <Tag color={v >= 60 ? 'green' : v >= 30 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: StoreProductDetail, b: StoreProductDetail) => a.gross_margin_pct - b.gross_margin_pct,
    },
  ];

  const channelColumns = [
    { title: '渠道', dataIndex: 'channel', width: 120, render: (v: string) => <Tag color="blue">{v}</Tag>, sorter: (a: ChannelSales, b: ChannelSales) => a.channel.localeCompare(b.channel) },
    { title: '店铺数', dataIndex: 'store_count', width: 80, sorter: (a: ChannelSales, b: ChannelSales) => a.store_count - b.store_count },
    { title: '销量', dataIndex: 'net_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: ChannelSales, b: ChannelSales) => a.net_qty - b.net_qty },
    { title: '销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ChannelSales, b: ChannelSales) => a.total_revenue - b.total_revenue, defaultSortOrder: 'descend' as const },
    { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: ChannelSales, b: ChannelSales) => a.total_cost - b.total_cost },
    { title: '佣金', dataIndex: 'commission_cost', width: 90, render: (v: number) => formatCurrency(v), sorter: (a: ChannelSales, b: ChannelSales) => a.commission_cost - b.commission_cost },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ChannelSales, b: ChannelSales) => a.gross_profit - b.gross_profit },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 60 ? 'green' : v >= 30 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: ChannelSales, b: ChannelSales) => a.gross_margin_pct - b.gross_margin_pct,
    },
    {
      title: '退货率',
      dataIndex: 'return_rate',
      width: 80,
      render: (v: number) => <span style={{ color: v > 10 ? '#ff4d4f' : '#666' }}>{formatPercent(v)}</span>,
      sorter: (a: ChannelSales, b: ChannelSales) => a.return_rate - b.return_rate,
    },
  ];

  const monthlyColumns = useMemo(() => {
    const cols: Array<Record<string, unknown>> = [
      { title: '排名', width: 55, render: (_: unknown, __: unknown, i: number) => i + 1 },
      { title: '店铺名称', dataIndex: 'store_name', ellipsis: true, width: 180 },
      { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    ];
    for (const p of monthlyPeriods) {
      cols.push({
        title: p,
        width: 110,
        render: (_: unknown, record: StoreMonthlyData) => {
          const m = record.months[p];
          return m ? formatCurrencyShort(m.revenue) : '-';
        },
        sorter: (a: StoreMonthlyData, b: StoreMonthlyData) => {
          const av = a.months[p]?.revenue || 0;
          const bv = b.months[p]?.revenue || 0;
          return av - bv;
        },
      });
    }
    cols.push({
      title: '总计',
      width: 120,
      render: (_: unknown, record: StoreMonthlyData) => formatCurrencyShort(record.total_revenue),
      sorter: (a: StoreMonthlyData, b: StoreMonthlyData) => a.total_revenue - b.total_revenue,
      defaultSortOrder: 'descend' as const,
    });
    return cols;
  }, [monthlyPeriods]);

  return (
    <div className="page-container">
      {/* 筛选器 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap align="center">
          <Select
            value={brand}
            onChange={(v) => setBrand(v)}
            style={{ width: 150 }}
            options={brandOptions}
          />
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 160 }}
            options={periods.map((p) => ({
              label: `${p.period}（¥${(p.net_revenue / 10000).toFixed(1)}万）`,
              value: p.period,
            }))}
            placeholder="选择月份"
          />
          <Button onClick={() => { loadOverviewData(); loadMonthlyData(); }} loading={loading}>
            刷新
          </Button>
        </Space>
      </Card>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          // ========== Tab1: 店铺总览 ==========
          {
            key: 'overview',
            label: '店铺总览',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={14}>
                  <Card title="店铺销售额/利润对比（TOP15）">
                    <ReactECharts option={overviewChartOption} style={{ height: 450 }} />
                  </Card>
                </Col>
                <Col xs={24} lg={10}>
                  <Card title="店铺排名明细">
                    <Table
                      dataSource={stores}
                      columns={storeColumns as ColumnsType<StoreSales>}
                      rowKey="store_id"
                      loading={loading}
                      size="small"
                      pagination={standardPagination(15)}
                      scroll={{ x: 950 }}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          // ========== Tab2: 店铺商品明细 ==========
          {
            key: 'store-products',
            label: '店铺商品明细',
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap align="center">
                    <span style={{ fontWeight: 600 }}>选择店铺:</span>
                    <Select
                      value={selectedStoreId}
                      onChange={(v) => setSelectedStoreId(v)}
                      style={{ width: 280 }}
                      showSearch
                      optionFilterProp="label"
                      options={storeOptions.map((s) => ({
                        label: `${s.store_name} [${s.platform}]`,
                        value: s.id,
                      }))}
                      placeholder="选择店铺"
                    />
                    <Input.Search
                      placeholder="搜索SKU/商品名"
                      allowClear
                      style={{ width: 200 }}
                      value={productSearch}
                      onChange={(e) => setProductSearch(e.target.value)}
                    />
                  </Space>
                </Card>

                {storeProductSummary && (
                  <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col xs={12} md={6}>
                      <Card size="small">
                        <Statistic
                          title="销售额"
                          value={storeProductSummary.total_revenue}
                          precision={2}
                          prefix="¥"
                          valueStyle={{ fontSize: 18 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} md={6}>
                      <Card size="small">
                        <Statistic
                          title="总成本"
                          value={storeProductSummary.total_cost}
                          precision={2}
                          prefix="¥"
                          valueStyle={{ fontSize: 18, color: '#999' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} md={6}>
                      <Card size="small">
                        <Statistic
                          title="毛利"
                          value={storeProductSummary.total_profit}
                          precision={2}
                          prefix="¥"
                          valueStyle={{
                            fontSize: 18,
                            color: storeProductSummary.total_profit >= 0 ? '#52c41a' : '#ff4d4f',
                          }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} md={6}>
                      <Card size="small">
                        <Statistic
                          title="毛利率 / SKU数"
                          value={storeProductSummary.gross_margin_pct}
                          precision={2}
                          suffix={`% / ${storeProductSummary.sku_count}个`}
                          valueStyle={{ fontSize: 18 }}
                        />
                      </Card>
                    </Col>
                  </Row>
                )}

                <Card title={`商品明细（${selectedStoreId ? storeOptions.find((s) => s.id === selectedStoreId)?.store_name : ''}）`}>
                  <Table
                    dataSource={filteredProducts}
                    columns={productDetailColumns as ColumnsType<StoreProductDetail>}
                    rowKey="product_id"
                    loading={productLoading}
                    size="small"
                    pagination={standardPagination(20)}
                    scroll={{ x: 1200 }}
                  />
                </Card>
              </div>
            ),
          },
          // ========== Tab3: 渠道分析 ==========
          {
            key: 'channel',
            label: '渠道分析',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={10}>
                  <Card title="渠道销售占比">
                    <ReactECharts option={channelChartOption} style={{ height: 380 }} />
                  </Card>
                </Col>
                <Col xs={24} lg={14}>
                  <Card title="渠道明细">
                    <Table
                      dataSource={channels}
                      columns={channelColumns}
                      rowKey="channel"
                      loading={loading}
                      size="small"
                      pagination={standardPagination(10)}
                      scroll={{ x: 850 }}
                    />
                  </Card>
                </Col>
                <Col xs={24}>
                  <Card title="平台 x 渠道 交叉热力图">
                    <ReactECharts option={crossHeatmapOption} style={{ height: 400 }} />
                  </Card>
                </Col>
              </Row>
            ),
          },
          // ========== Tab4: 月度趋势 ==========
          {
            key: 'monthly',
            label: '月度趋势',
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap align="center">
                    <span style={{ fontWeight: 600 }}>指标:</span>
                    <Select
                      value={monthlyMetric}
                      onChange={(v) => setMonthlyMetric(v as 'revenue' | 'profit')}
                      style={{ width: 120 }}
                      options={[
                        { label: '销售额', value: 'revenue' },
                        { label: '利润', value: 'profit' },
                      ]}
                    />
                    <span style={{ fontWeight: 600 }}>展示店铺数:</span>
                    <Select
                      value={monthlyTopN}
                      onChange={(v) => setMonthlyTopN(v)}
                      style={{ width: 80 }}
                      options={[
                        { label: 'TOP 5', value: 5 },
                        { label: 'TOP 10', value: 10 },
                        { label: 'TOP 15', value: 15 },
                        { label: 'TOP 20', value: 20 },
                      ]}
                    />
                  </Space>
                </Card>

                <Card title={`各店铺月度${monthlyMetric === 'revenue' ? '销售额' : '利润'}趋势（${monthlyPeriods.join(' / ')}）`}>
                  <ReactECharts option={monthlyChartOption} style={{ height: 450 }} />
                </Card>

                <Card title="月度明细对比" style={{ marginTop: 16 }}>
                  <Table
                    dataSource={monthlyStores}
                    columns={monthlyColumns}
                    rowKey="store_id"
                    loading={monthlyLoading}
                    size="small"
                    pagination={standardPagination(20)}
                    scroll={{ x: 180 + monthlyPeriods.length * 110 }}
                  />
                </Card>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
