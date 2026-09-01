import { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, DatePicker, Select, Button, Space, Tabs, Spin, Segmented } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { profitApi, salesApi, exportApi } from '../api';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import type { ProfitSummary, StoreProfit, ProductProfit, LowMarginItem, StoreOption } from '../types';
import { formatCurrency, formatPercent, formatNumber } from '../utils/format';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

type BrandType = '全部' | '慕咖STTOKE' | '慕咖（MOODY）' | 'MoodyCoffee' | '巴恩天然';

const brandOptions: { label: string; value: BrandType }[] = [
  { label: '全部品牌', value: '全部' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

export default function Profit() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [selectedStore, setSelectedStore] = useState<string | undefined>(undefined);
  const [brand, setBrand] = useState<BrandType>('全部');
  const { periods, month, setMonth } = usePeriods();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);

  const [summary, setSummary] = useState<ProfitSummary | null>(null);
  const [storeProfits, setStoreProfits] = useState<StoreProfit[]>([]);
  const [productProfits, setProductProfits] = useState<ProductProfit[]>([]);
  const [lowMargin, setLowMargin] = useState<LowMarginItem[]>([]);
  const [storeOptions, setStoreOptions] = useState<StoreOption[]>([]);
  const [dailyTrend, setDailyTrend] = useState<{ date: string; revenue: number; gross_profit: number; net_profit: number }[]>([]);
  const [exporting, setExporting] = useState(false);

  const params: Record<string, string> = {};
  if (month) params.month = month;
  if (dateRange) {
    params.start_date = dateRange[0].format('YYYY-MM-DD');
    params.end_date = dateRange[1].format('YYYY-MM-DD');
  }
  if (selectedStore) params.store_id = selectedStore;
  if (brand !== '全部') params.brand = brand;

  const loadData = useCallback(() => {
    if (!month) return;
    setLoading(true);
    const brandParams = brand !== '全部' ? { brand } : {};
    Promise.all([
      profitApi.summary({ ...params, ...brandParams }),
      profitApi.byStore({ ...params, ...brandParams, limit: 100 }),
      profitApi.byProduct({ ...brandParams, limit: 100 }),
      profitApi.lowMargin({ ...brandParams, limit: 50 }),
      profitApi.dailyTrend({ ...params, ...brandParams }),
    ])
      .then(([s, sp, pp, lm, dt]) => {
        setSummary(s.data.data);
        setStoreProfits(sp.data.data.stores);
        setProductProfits(pp.data.data.products);
        setLowMargin(lm.data.data.items);
        setDailyTrend(dt.data.data.daily);
      })
      .finally(() => setLoading(false));
  }, [dateRange, selectedStore, brand, month]);

  useEffect(() => {
    salesApi.stores().then((res) => setStoreOptions(res.data.data));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const exportParams: Record<string, string> = {};
      if (month) exportParams.month = month;
      if (brand !== '全部') exportParams.brand = brand;
      const resp = await exportApi.profit(exportParams);
      const url = window.URL.createObjectURL(resp.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Profit_${month || 'all'}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } finally { setExporting(false); }
  };

  // ===== 利润瀑布图 =====
  const waterfallOption = () => {
    if (!summary) return {};
    const rev = Math.round(summary.revenue);
    const cost = Math.round(summary.net_cost);
    const grossProfit = Math.round(summary.gross_profit);
    const commission = Math.round(summary.commission_cost);
    const shipping = Math.round(summary.shipping_cost);
    const packaging = Math.round(summary.packaging_cost);
    const netProfit = Math.round(summary.net_profit);

    // Waterfall: each step is [base, value, total]
    // bar1: 销售收入 — full bar from 0 to rev
    // bar2: 产品成本 — floating bar from grossProfit to rev (decrease)
    // bar3: 毛利 — full bar from 0 to grossProfit (subtotal)
    // bar4: 佣金 — floating bar from (grossProfit - commission) to grossProfit
    // bar5: 邮资 — floating bar
    // bar6: 包装 — floating bar
    // bar7: 净利润 — full bar from 0 to netProfit (subtotal)

    const afterCommission = grossProfit - commission;
    const afterShipping = afterCommission - shipping;
    const afterPackaging = afterShipping - packaging;

    const labels = ['销售收入', '产品成本', '毛利', '佣金', '邮资成本', '包装成本', '净利润'];
    // For each step: [transparent_base, visible_bar]
    const data = [
      [0, rev],                    // 销售收入: 0 to rev
      [grossProfit, cost],         // 产品成本: grossProfit to rev (decrease)
      [0, grossProfit],            // 毛利: subtotal
      [afterCommission, commission],// 佣金: decrease
      [afterShipping, shipping],   // 邮资: decrease
      [afterPackaging, packaging], // 包装: decrease
      [0, netProfit],              // 净利润: subtotal
    ];

    const colors = ['#1677ff', '#ff4d4f', '#52c41a', '#fa8c16', '#fa8c16', '#fa8c16', '#722ed1'];

    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
        formatter: (params: Array<{ dataIndex: number; value: number[]; name: string }>) => {
          const p = params[0];
          const idx = p.dataIndex;
          const total = idx === 0 ? rev : idx === 2 ? grossProfit : idx === 6 ? netProfit : data[idx][0] + data[idx][1];
          return `${p.name}<br/>金额: ¥${(data[idx][1]).toLocaleString()}<br/>累计: ¥${total.toLocaleString()}`;
        },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category' as const, data: labels, axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` } },
      series: [
        {
          type: 'bar',
          stack: 'waterfall',
          itemStyle: { color: 'transparent' },
          data: data.map((d) => d[0]),
          silent: true,
        },
        {
          type: 'bar',
          stack: 'waterfall',
          data: data.map((d, i) => ({
            value: d[1],
            itemStyle: {
              color: colors[i],
              borderRadius: i === 0 || i === 2 || i === 6 ? [4, 4, 0, 0] : [0, 0, 0, 0],
            },
          })),
          label: {
            show: true,
            position: 'top',
            formatter: (p: { dataIndex: number }) => {
              const val = data[p.dataIndex][1];
              const sign = p.dataIndex === 1 || p.dataIndex === 3 || p.dataIndex === 4 || p.dataIndex === 5 ? '-' : '';
              return `${sign}¥${Math.abs(val).toLocaleString()}`;
            },
            fontSize: 11,
          },
          barWidth: '50%',
        },
      ],
    };
  };

  // ===== SKU利润矩阵 =====
  const matrixOption = () => {
    const data = productProfits.filter((p) => p.net_revenue > 0);
    if (data.length === 0) return {};

    // Calculate median for quadrant lines
    const revenues = data.map((d) => d.net_revenue).sort((a, b) => a - b);
    const margins = data.map((d) => d.net_margin_pct).sort((a, b) => a - b);
    const medianRev = revenues[Math.floor(revenues.length / 2)] || 0;
    const medianMargin = margins[Math.floor(margins.length / 2)] || 0;

    // Color by quadrant
    const getColor = (rev: number, margin: number) => {
      if (rev >= medianRev && margin >= medianMargin) return '#52c41a'; // 高销售高利润
      if (rev >= medianRev && margin < medianMargin) return '#fa8c16';  // 高销售低利润
      if (rev < medianRev && margin >= medianMargin) return '#1677ff';  // 低销售高利润
      return '#ff4d4f'; // 低销售低利润
    };

    return {
      tooltip: {
        formatter: (p: { data: number[]; data: { name: string } }) => {
          return `${p.data.name}<br/>销售额: ¥${p.data[0].toLocaleString()}<br/>净利率: ${p.data[1].toFixed(1)}%<br/>净利润: ¥${p.data[2].toLocaleString()}`;
        },
      },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: {
        type: 'value' as const,
        name: '销售额(¥)',
        nameLocation: 'middle' as const,
        nameGap: 30,
        axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` },
        splitLine: { show: true, lineStyle: { type: 'dashed' as const } },
      },
      yAxis: {
        type: 'value' as const,
        name: '净利率(%)',
        nameLocation: 'middle' as const,
        nameGap: 40,
        splitLine: { show: true, lineStyle: { type: 'dashed' as const } },
      },
      series: [
        {
          type: 'scatter',
          symbolSize: (val: number[]) => Math.max(8, Math.min(40, Math.sqrt(val[2]) / 10)),
          data: data.map((d) => ({
            name: d.product_name,
            value: [d.net_revenue, d.net_margin_pct, d.net_profit],
            itemStyle: { color: getColor(d.net_revenue, d.net_margin_pct), opacity: 0.7 },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed' as const, color: '#999' },
            data: [
              { xAxis: medianRev, label: { formatter: '中位销售额' } },
              { yAxis: medianMargin, label: { formatter: '中位净利率' } },
            ],
          },
          markArea: {
            silent: true,
            itemStyle: { opacity: 0.03 },
            data: [
              [{ coord: [medianRev, medianMargin], itemStyle: { color: '#52c41a' } }, { coord: [Infinity, Infinity] }],
              [{ coord: [medianRev, -Infinity], itemStyle: { color: '#fa8c16' } }, { coord: [Infinity, medianMargin] }],
              [{ coord: [-Infinity, medianMargin], itemStyle: { color: '#1677ff' } }, { coord: [medianRev, Infinity] }],
              [{ coord: [-Infinity, -Infinity], itemStyle: { color: '#ff4d4f' } }, { coord: [medianRev, medianMargin] }],
            ],
          },
        },
      ],
    };
  };

  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['销售额', '毛利', '净利润'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: dailyTrend.map((d) => d.date),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => `${(v / 10000).toFixed(0)}万` } },
    series: [
      { name: '销售额', type: 'line', smooth: true, areaStyle: { opacity: 0.1 }, itemStyle: { color: '#1677ff' }, data: dailyTrend.map((d) => Math.round(d.revenue)) },
      { name: '毛利', type: 'line', smooth: true, itemStyle: { color: '#52c41a' }, data: dailyTrend.map((d) => Math.round(d.gross_profit)) },
      { name: '净利润', type: 'line', smooth: true, itemStyle: { color: '#fa8c16' }, data: dailyTrend.map((d) => Math.round(d.net_profit)) },
    ],
  };

  const storeColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: '店铺', dataIndex: 'store_name', ellipsis: true, sorter: (a: StoreProfit, b: StoreProfit) => a.store_name.localeCompare(b.store_name) },
    { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag>, filters: [...new Set(storeProfits.map(s => s.platform))].map(p => ({ text: p, value: p })), onFilter: (v: string | number | boolean, r: StoreProfit) => r.platform === v },
    { title: '订单数', dataIndex: 'order_count', width: 80, render: (v: number) => formatNumber(v), sorter: (a: StoreProfit, b: StoreProfit) => a.order_count - b.order_count },
    { title: '收入', dataIndex: 'revenue', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: StoreProfit, b: StoreProfit) => a.revenue - b.revenue, defaultSortOrder: 'descend' as const },
    { title: '毛利', dataIndex: 'gross_profit', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: StoreProfit, b: StoreProfit) => a.gross_profit - b.gross_profit },
    { title: '邮资成本', dataIndex: 'shipping_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: StoreProfit, b: StoreProfit) => a.shipping_cost - b.shipping_cost },
    { title: '包装成本', dataIndex: 'packaging_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: StoreProfit, b: StoreProfit) => a.packaging_cost - b.packaging_cost },
    { title: '贡献利润', dataIndex: 'contribution_profit', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: StoreProfit, b: StoreProfit) => a.contribution_profit - b.contribution_profit },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: StoreProfit, b: StoreProfit) => a.gross_margin_pct - b.gross_margin_pct,
    },
  ];

  const productColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: 'SKU', dataIndex: 'sku', width: 120, sorter: (a: ProductProfit, b: ProductProfit) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true, sorter: (a: ProductProfit, b: ProductProfit) => a.product_name.localeCompare(b.product_name) },
    { title: '店铺', dataIndex: 'store_name', width: 150, ellipsis: true, sorter: (a: ProductProfit, b: ProductProfit) => a.store_name.localeCompare(b.store_name) },
    { title: '发货量', dataIndex: 'ship_qty', width: 70, render: (v: number) => formatNumber(v), sorter: (a: ProductProfit, b: ProductProfit) => a.ship_qty - b.ship_qty },
    { title: '退货量', dataIndex: 'return_qty', width: 70, render: (v: number) => formatNumber(v), sorter: (a: ProductProfit, b: ProductProfit) => a.return_qty - b.return_qty },
    { title: '净销量', dataIndex: 'net_qty', width: 70, render: (v: number) => formatNumber(v), sorter: (a: ProductProfit, b: ProductProfit) => a.net_qty - b.net_qty },
    { title: '净收入', dataIndex: 'net_revenue', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: ProductProfit, b: ProductProfit) => a.net_revenue - b.net_revenue, defaultSortOrder: 'descend' as const },
    { title: '净成本', dataIndex: 'net_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: ProductProfit, b: ProductProfit) => a.net_cost - b.net_cost },
    { title: '净利润', dataIndex: 'net_profit', width: 110, render: (v: number) => formatCurrency(v), sorter: (a: ProductProfit, b: ProductProfit) => a.net_profit - b.net_profit },
    {
      title: '净利率',
      dataIndex: 'net_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : v >= 0 ? 'volcano' : 'red'}>{formatPercent(v)}</Tag>,
      sorter: (a: ProductProfit, b: ProductProfit) => a.net_margin_pct - b.net_margin_pct,
    },
  ];

  const lowMarginColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 120, sorter: (a: LowMarginItem, b: LowMarginItem) => a.sku.localeCompare(b.sku) },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true, sorter: (a: LowMarginItem, b: LowMarginItem) => a.product_name.localeCompare(b.product_name) },
    { title: '分类', dataIndex: 'category', width: 100, render: (v: string | null) => v || '-', filters: [...new Set(lowMargin.map(i => i.category).filter(Boolean))].map(c => ({ text: c, value: c })), onFilter: (v: string | number | boolean, r: LowMarginItem) => r.category === v },
    { title: '店铺', dataIndex: 'store_name', width: 150, ellipsis: true, sorter: (a: LowMarginItem, b: LowMarginItem) => a.store_name.localeCompare(b.store_name) },
    { title: '净销量', dataIndex: 'net_qty', width: 70, render: (v: number) => formatNumber(v), sorter: (a: LowMarginItem, b: LowMarginItem) => a.net_qty - b.net_qty },
    { title: '净收入', dataIndex: 'net_revenue', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: LowMarginItem, b: LowMarginItem) => a.net_revenue - b.net_revenue },
    { title: '净成本', dataIndex: 'net_cost', width: 100, render: (v: number) => formatCurrency(v), sorter: (a: LowMarginItem, b: LowMarginItem) => a.net_cost - b.net_cost },
    { title: '净利润', dataIndex: 'net_profit', width: 100, render: (v: number) => <span style={{ color: v < 0 ? '#ff4d4f' : '#52c41a' }}>{formatCurrency(v)}</span>, sorter: (a: LowMarginItem, b: LowMarginItem) => a.net_profit - b.net_profit },
    {
      title: '净利率',
      dataIndex: 'net_margin_pct',
      width: 100,
      render: (v: number) => <Tag color={v < 0 ? 'red' : 'orange'}>{formatPercent(v)}</Tag>,
      sorter: (a: LowMarginItem, b: LowMarginItem) => a.net_margin_pct - b.net_margin_pct,
    },
    {
      title: '风险',
      dataIndex: 'risk_level',
      width: 80,
      render: (v: string) => <Tag color={v === 'loss' ? 'red' : 'orange'}>{v === 'loss' ? '亏损' : '低毛利'}</Tag>,
      filters: [{ text: '亏损', value: 'loss' }, { text: '低毛利', value: 'low_margin' }],
      onFilter: (v: string | number | boolean, r: LowMarginItem) => r.risk_level === v,
    },
  ];

  if (loading && !summary) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', padding: 100 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* 品牌切换器 + 月份选择器 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Segmented
            options={brandOptions}
            value={brand}
            onChange={(v) => setBrand(v as BrandType)}
            size="large"
          />
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 150 }}
            size="large"
            options={periods.map((p) => ({
              label: `${p.period}（¥${(p.net_revenue / 10000).toFixed(1)}万）`,
              value: p.period,
            }))}
            placeholder="选择月份"
          />
        </Space>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
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
            key: 'overview',
            label: '利润概览',
            children: (
              <>
                <Row gutter={[16, 16]}>
                  <Col xs={12} md={6}>
                    <Card>
                      <Statistic title="总收入" value={summary?.revenue || 0} precision={2} prefix="¥" valueStyle={{ color: '#1677ff' }} />
                    </Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card>
                      <Statistic title="毛利润" value={summary?.gross_profit || 0} precision={2} prefix="¥" valueStyle={{ color: '#52c41a' }} />
                    </Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card>
                      <Statistic title="贡献利润" value={summary?.contribution_profit || 0} precision={2} prefix="¥" valueStyle={{ color: '#fa8c16' }} />
                    </Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card>
                      <Statistic title="净利润" value={summary?.net_profit || 0} precision={2} prefix="¥" valueStyle={{ color: '#722ed1' }} />
                    </Card>
                  </Col>
                </Row>
                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="毛利率" value={summary?.gross_margin_pct || 0} precision={2} suffix="%" /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="净利率" value={summary?.net_margin_pct || 0} precision={2} suffix="%" /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="邮费收入" value={summary?.shipping_fee || 0} precision={2} prefix="¥" /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="折扣总额" value={summary?.discount || 0} precision={2} prefix="¥" /></Card>
                  </Col>
                </Row>

                {/* 利润瀑布图 */}
                <Card title="利润瀑布图" style={{ marginTop: 16 }}>
                  <ReactECharts option={waterfallOption()} style={{ height: 400 }} />
                </Card>

                {/* 成本结构 */}
                <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                  <Col xs={24} md={8}>
                    <Card size="small" title="产品成本">
                      <Statistic value={summary?.net_cost || 0} precision={2} prefix="¥" valueStyle={{ color: '#ff4d4f' }} />
                      <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                        占收入 {summary && summary.revenue > 0 ? ((summary.net_cost / summary.revenue) * 100).toFixed(1) : 0}%
                      </div>
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card size="small" title="佣金成本">
                      <Statistic value={summary?.commission_cost || 0} precision={2} prefix="¥" valueStyle={{ color: '#fa8c16' }} />
                      <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                        占收入 {summary && summary.revenue > 0 ? ((summary.commission_cost / summary.revenue) * 100).toFixed(1) : 0}%
                      </div>
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card size="small" title="物流包装">
                      <Statistic value={(summary?.shipping_cost || 0) + (summary?.packaging_cost || 0)} precision={2} prefix="¥" valueStyle={{ color: '#fa8c16' }} />
                      <div style={{ marginTop: 8, color: '#999', fontSize: 12 }}>
                        邮资 ¥{summary?.shipping_cost?.toFixed(0) || 0} + 包装 ¥{summary?.packaging_cost?.toFixed(0) || 0}
                      </div>
                    </Card>
                  </Col>
                </Row>

                <Card title="利润趋势" style={{ marginTop: 16 }}>
                  <ReactECharts option={trendOption} style={{ height: 360 }} />
                </Card>
              </>
            ),
          },
          {
            key: 'matrix',
            label: 'SKU利润矩阵',
            children: (
              <>
                <Card title="SKU利润四象限矩阵" extra={
                  <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#666' }}>
                    <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', backgroundColor: '#52c41a', marginRight: 4 }} />高销售高利润</span>
                    <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', backgroundColor: '#fa8c16', marginRight: 4 }} />高销售低利润</span>
                    <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', backgroundColor: '#1677ff', marginRight: 4 }} />低销售高利润</span>
                    <span><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', backgroundColor: '#ff4d4f', marginRight: 4 }} />低销售低利润</span>
                  </div>
                }>
                  <ReactECharts option={matrixOption()} style={{ height: 500 }} />
                </Card>
                <Card title="象限说明" style={{ marginTop: 16 }}>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={6}>
                      <Card size="small" style={{ borderLeft: '4px solid #52c41a' }}>
                        <h4 style={{ color: '#52c41a' }}>明星产品</h4>
                        <p style={{ fontSize: 12, color: '#666' }}>高销售 + 高利润。核心利润来源，应保障库存充足，持续投入。</p>
                      </Card>
                    </Col>
                    <Col xs={24} md={6}>
                      <Card size="small" style={{ borderLeft: '4px solid #fa8c16' }}>
                        <h4 style={{ color: '#fa8c16' }}>关注产品</h4>
                        <p style={{ fontSize: 12, color: '#666' }}>高销售 + 低利润。销量大但利润薄，需优化成本或调整定价。</p>
                      </Card>
                    </Col>
                    <Col xs={24} md={6}>
                      <Card size="small" style={{ borderLeft: '4px solid #1677ff' }}>
                        <h4 style={{ color: '#1677ff' }}>潜力产品</h4>
                        <p style={{ fontSize: 12, color: '#666' }}>低销售 + 高利润。利润率好但量小，可加大推广或扩渠道。</p>
                      </Card>
                    </Col>
                    <Col xs={24} md={6}>
                      <Card size="small" style={{ borderLeft: '4px solid #ff4d4f' }}>
                        <h4 style={{ color: '#ff4d4f' }}>淘汰候选</h4>
                        <p style={{ fontSize: 12, color: '#666' }}>低销售 + 低利润。考虑清仓退出，释放库存资金。</p>
                      </Card>
                    </Col>
                  </Row>
                </Card>
              </>
            ),
          },
          {
            key: 'store',
            label: '店铺利润',
            children: (
              <Card>
                <Table
                  dataSource={storeProfits}
                  columns={storeColumns}
                  rowKey="store_id"
                  loading={loading}
                  size="small"
                  pagination={standardPagination(20)}
                  scroll={{ x: 900 }}
                />
              </Card>
            ),
          },
          {
            key: 'product',
            label: '商品利润',
            children: (
              <Card>
                <Table
                  dataSource={productProfits}
                  columns={productColumns}
                  rowKey={(r) => `${r.product_id}-${r.store_name}`}
                  loading={loading}
                  size="small"
                  pagination={standardPagination(20)}
                  scroll={{ x: 1000 }}
                />
              </Card>
            ),
          },
          {
            key: 'risk',
            label: <span>低毛利预警 {lowMargin.length > 0 && <Tag color="red" style={{ marginLeft: 4 }}>{lowMargin.length}</Tag>}</span>,
            children: (
              <Card title={`低毛利 / 亏损商品预警（共 ${lowMargin.length} 个）`}>
                <Table
                  dataSource={lowMargin}
                  columns={lowMarginColumns}
                  rowKey={(r) => `${r.sku}-${r.store_name}`}
                  loading={loading}
                  size="small"
                  pagination={standardPagination(20)}
                  scroll={{ x: 900 }}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
