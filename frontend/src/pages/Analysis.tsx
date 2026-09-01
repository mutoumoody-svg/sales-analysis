import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Row, Col, Card, Table, Spin, Tag, Tabs, Select, Button, Tooltip, Space, Statistic, Empty, Alert, Typography,
} from 'antd';
import {
  DownloadOutlined, CrownOutlined, RiseOutlined, FallOutlined, WalletOutlined,
  LineChartOutlined, DollarOutlined, WarningOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { analysisApi, exportApi, salesApi } from '../api';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import { formatCurrency, formatCurrencyShort, formatNumber, formatPercent } from '../utils/format';
import type {
  ABCAnalysis, GMROIAnalysis, SalesForecast, CashflowForecast, OptimalInterval,
  ABCItem, GMROIItem, IntervalItem,
} from '../types';

type BrandType = '全部' | '慕咖STTOKE' | '慕咖（MOODY）' | 'MoodyCoffee' | '巴恩天然';

const brandOptions: { label: string; value: BrandType }[] = [
  { label: '全部品牌', value: '全部' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

const { Text } = Typography;

const gradeColors: Record<string, string> = { A: '#ff4d4f', B: '#faad14', C: '#52c41a' };
const statusColors: Record<string, string> = { good: '#52c41a', poor: '#ff4d4f', no_inventory: '#bfbfbf' };
const statusText: Record<string, string> = { good: '盈利', poor: '亏损', no_inventory: '无库存' };

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

export default function Analysis() {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('abc');
  const [brand, setBrand] = useState<BrandType>('全部');
  const { periods, month, setMonth } = usePeriods();

  const [abcData, setAbcData] = useState<ABCAnalysis | null>(null);
  const [gmroiData, setGmroiData] = useState<GMROIAnalysis | null>(null);
  const [forecastData, setForecastData] = useState<SalesForecast | null>(null);
  const [cashflowData, setCashflowData] = useState<CashflowForecast | null>(null);
  const [intervalData, setIntervalData] = useState<OptimalInterval | null>(null);
  const [exporting, setExporting] = useState(false);

  const brandParams = brand === '全部' ? {} : { brand };

  const loadABC = useCallback(async (m: string, b: BrandType) => {
    if (!m) return;
    setLoading(true);
    try {
      const bp = b === '全部' ? {} : { brand: b };
      const resp = await analysisApi.abc({ ...bp, period: m });
      setAbcData(resp.data);
    } finally { setLoading(false); }
  }, []);

  const loadGMROI = useCallback(async (m: string, b: BrandType) => {
    if (!m) return;
    setLoading(true);
    try {
      const bp = b === '全部' ? {} : { brand: b };
      const resp = await analysisApi.gmroi({ ...bp, period: m });
      setGmroiData(resp.data);
    } finally { setLoading(false); }
  }, []);

  const loadForecast = useCallback(async (b: BrandType) => {
    setLoading(true);
    try {
      const bp = b === '全部' ? {} : { brand: b };
      const resp = await analysisApi.forecast({ ...bp, forecast_months: 3 });
      setForecastData(resp.data);
    } finally { setLoading(false); }
  }, []);

  const loadCashflow = useCallback(async (b: BrandType) => {
    setLoading(true);
    try {
      const bp = b === '全部' ? {} : { brand: b };
      const resp = await analysisApi.cashflow({ ...bp, forecast_months: 3 });
      setCashflowData(resp.data);
    } finally { setLoading(false); }
  }, []);

  const loadInterval = useCallback(async (b: BrandType) => {
    setLoading(true);
    try {
      const bp = b === '全部' ? {} : { brand: b };
      const resp = await analysisApi.interval({ ...bp });
      setIntervalData(resp.data);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (activeTab === 'abc' && month) loadABC(month, brand);
    else if (activeTab === 'gmroi' && month) loadGMROI(month, brand);
    else if (activeTab === 'forecast') loadForecast(brand);
    else if (activeTab === 'cashflow') loadCashflow(brand);
    else if (activeTab === 'interval') loadInterval(brand);
  }, [activeTab, month, brand]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const params = { ...brandParams, ...(month ? { period: month, month } : {}) };
      let resp;
      if (activeTab === 'abc') resp = await exportApi.abc({ ...brandParams, period: month });
      else if (activeTab === 'gmroi') resp = await exportApi.gmroi({ ...brandParams, period: month });
      else if (activeTab === 'forecast') resp = await exportApi.forecast({ ...brandParams });
      else if (activeTab === 'cashflow') resp = await exportApi.cashflow({ ...brandParams });
      else resp = await exportApi.abc({ ...brandParams, period: month });

      if (resp && resp.data) {
        downloadBlob(resp.data as Blob, `Analysis_${activeTab}_${Date.now()}.xlsx`);
      }
    } catch (e) {
      console.error('Export failed:', e);
    } finally {
      setExporting(false);
    }
  };

  // ============================================================
  // ABC Charts
  // ============================================================
  const abcChartOption = useMemo(() => {
    if (!abcData?.items?.length) return null;
    const top30 = abcData.items.slice(0, 30);
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['销售额', '累计占比'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: top30.map(i => i.sku),
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: [
        { type: 'value', name: '销售额', position: 'left' },
        { type: 'value', name: '累计占比%', position: 'right', max: 100 },
      ],
      series: [
        {
          name: '销售额',
          type: 'bar',
          data: top30.map(i => ({
            value: i.revenue,
            itemStyle: { color: gradeColors[i.grade] },
          })),
          barMaxWidth: 30,
        },
        {
          name: '累计占比',
          type: 'line',
          yAxisIndex: 1,
          data: top30.map(i => i.cum_pct),
          smooth: true,
          lineStyle: { width: 2, color: '#1890ff' },
          itemStyle: { color: '#1890ff' },
        },
      ],
    };
  }, [abcData]);

  const abcPieOption = useMemo(() => {
    if (!abcData?.summary) return null;
    const s = abcData.summary;
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        data: [
          { name: `A类 (${s.a_count}个)`, value: s.a_revenue, itemStyle: { color: '#ff4d4f' } },
          { name: `B类 (${s.b_count}个)`, value: s.b_revenue, itemStyle: { color: '#faad14' } },
          { name: `C类 (${s.c_count}个)`, value: s.c_revenue, itemStyle: { color: '#52c41a' } },
        ],
        label: { formatter: '{b}\n{d}%' },
      }],
    };
  }, [abcData]);

  // ============================================================
  // GMROI Chart
  // ============================================================
  const gmroiChartOption = useMemo(() => {
    if (!gmroiData?.items?.length) return null;
    const items = gmroiData.items.filter(i => i.gmroi !== null).slice(0, 30);
    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.data[2]}<br/>库存成本: ¥${p.data[0]?.toFixed(0)}<br/>GMROI: ${p.data[1]?.toFixed(1)}%`,
      },
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
      xAxis: { type: 'value', name: '库存成本', nameLocation: 'middle', nameGap: 30 },
      yAxis: { type: 'value', name: 'GMROI(%)' },
      series: [{
        type: 'scatter',
        data: items.map(i => [i.inv_cost, i.gmroi, i.sku]),
        symbolSize: (val: number[]) => Math.max(8, Math.min(30, Math.sqrt(Math.abs(val[1])))),
        itemStyle: {
          color: (p: any) => p.data[1] > 0 ? '#52c41a' : '#ff4d4f',
          opacity: 0.7,
        },
      }],
    };
  }, [gmroiData]);

  // ============================================================
  // Forecast Chart
  // ============================================================
  const forecastChartOption = useMemo(() => {
    if (!forecastData) return null;
    const history = forecastData.history;
    const forecast = forecastData.forecast;
    const allPeriods = [...history.map(h => h.period), ...forecast.map(f => f.period)];
    const histRevenue = history.map(h => h.revenue);
    const foreRevenue = [...history.map(() => null), ...forecast.map(f => f.revenue)];
    // 连接线: 最后一个历史点到第一个预测点
    if (history.length > 0 && forecast.length > 0) {
      foreRevenue[history.length - 1] = history[history.length - 1].revenue;
    }
    const histProfit = history.map(h => h.profit);
    const foreProfit = [...history.map(() => null), ...forecast.map(f => f.profit)];
    if (history.length > 0 && forecast.length > 0) {
      foreProfit[history.length - 1] = history[history.length - 1].profit;
    }

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['历史销售额', '预测销售额', '历史利润', '预测利润'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: allPeriods },
      yAxis: { type: 'value', name: '金额' },
      series: [
        {
          name: '历史销售额',
          type: 'line',
          data: histRevenue,
          smooth: true,
          lineStyle: { width: 3 },
          itemStyle: { color: '#1890ff' },
          areaStyle: { opacity: 0.1 },
        },
        {
          name: '预测销售额',
          type: 'line',
          data: foreRevenue,
          smooth: true,
          lineStyle: { width: 3, type: 'dashed' },
          itemStyle: { color: '#1890ff' },
        },
        {
          name: '历史利润',
          type: 'line',
          data: histProfit,
          smooth: true,
          lineStyle: { width: 2 },
          itemStyle: { color: '#52c41a' },
        },
        {
          name: '预测利润',
          type: 'line',
          data: foreProfit,
          smooth: true,
          lineStyle: { width: 2, type: 'dashed' },
          itemStyle: { color: '#52c41a' },
        },
      ],
    };
  }, [forecastData]);

  // ============================================================
  // Cashflow Chart
  // ============================================================
  const cashflowChartOption = useMemo(() => {
    if (!cashflowData) return null;
    const all = [...cashflowData.history, ...cashflowData.forecast];
    const periods = all.map(i => i.period);
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['流入', '成本流出', '费用流出', '净现金流', '累计现金流'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: periods },
      yAxis: [
        { type: 'value', name: '月度', position: 'left' },
        { type: 'value', name: '累计', position: 'right' },
      ],
      series: [
        { name: '流入', type: 'bar', data: all.map(i => i.inflow), itemStyle: { color: '#52c41a', opacity: 0.7 } },
        { name: '成本流出', type: 'bar', data: all.map(i => -i.outflow_cost), itemStyle: { color: '#ff4d4f', opacity: 0.7 } },
        { name: '费用流出', type: 'bar', data: all.map(i => -i.outflow_expense), itemStyle: { color: '#faad14', opacity: 0.7 } },
        { name: '净现金流', type: 'line', data: all.map(i => i.net_cashflow), smooth: true, lineStyle: { width: 2 } },
        { name: '累计现金流', type: 'line', yAxisIndex: 1, data: all.map(i => i.cumulative), smooth: true, lineStyle: { width: 2, type: 'dashed' } },
      ],
    };
  }, [cashflowData]);

  // ============================================================
  // Interval Chart
  // ============================================================
  const intervalChartOption = useMemo(() => {
    if (!intervalData?.intervals?.length) return null;
    const intervals = intervalData.intervals;
    const optimal = intervalData.optimal;
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['总利润', '毛利率%'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: intervals.map(i => i.discount_range) },
      yAxis: [
        { type: 'value', name: '利润' },
        { type: 'value', name: '毛利率%', position: 'right' },
      ],
      series: [
        {
          name: '总利润',
          type: 'bar',
          data: intervals.map(i => ({
            value: i.profit,
            itemStyle: { color: optimal && i.discount_range === optimal.discount_range ? '#ff4d4f' : '#1890ff' },
          })),
          barMaxWidth: 40,
        },
        {
          name: '毛利率%',
          type: 'line',
          yAxisIndex: 1,
          data: intervals.map(i => i.margin_pct),
          smooth: true,
          lineStyle: { width: 2, color: '#52c41a' },
          itemStyle: { color: '#52c41a' },
        },
      ],
    };
  }, [intervalData]);

  // ============================================================
  // Table Columns
  // ============================================================
  const abcColumns = [
    {
      title: '等级', dataIndex: 'grade', key: 'grade', width: 60, fixed: 'left',
      filters: [{ text: 'A', value: 'A' }, { text: 'B', value: 'B' }, { text: 'C', value: 'C' }],
      onFilter: (v: any, r: ABCItem) => r.grade === v,
      render: (g: string) => <Tag color={gradeColors[g]} style={{ fontWeight: 'bold' }}>{g}</Tag>,
    },
    { title: 'SKU', dataIndex: 'sku', key: 'sku', width: 120, fixed: 'left', sorter: (a: ABCItem, b: ABCItem) => a.sku.localeCompare(b.sku) },
    { title: '产品名称', dataIndex: 'product_name', key: 'product_name', ellipsis: true, sorter: (a: ABCItem, b: ABCItem) => a.product_name.localeCompare(b.product_name) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 120, sorter: (a: ABCItem, b: ABCItem) => (a.brand || '').localeCompare(b.brand || '') },
    { title: '销量', dataIndex: 'qty', key: 'qty', width: 80, sorter: (a: ABCItem, b: ABCItem) => a.qty - b.qty, render: (v: number) => formatNumber(v) },
    { title: '销售额', dataIndex: 'revenue', key: 'revenue', width: 120, sorter: (a: ABCItem, b: ABCItem) => a.revenue - b.revenue, render: (v: number) => formatCurrencyShort(v) },
    { title: '利润', dataIndex: 'profit', key: 'profit', width: 120, sorter: (a: ABCItem, b: ABCItem) => a.profit - b.profit, render: (v: number) => formatCurrencyShort(v) },
    { title: '毛利率', dataIndex: 'margin_pct', key: 'margin_pct', width: 80, sorter: (a: ABCItem, b: ABCItem) => a.margin_pct - b.margin_pct, render: (v: number) => `${v}%` },
    { title: '累计占比', dataIndex: 'cum_pct', key: 'cum_pct', width: 90, sorter: (a: ABCItem, b: ABCItem) => a.cum_pct - b.cum_pct, render: (v: number) => `${v}%` },
  ];

  const gmroiColumns = [
    { title: 'SKU', dataIndex: 'sku', key: 'sku', width: 120, fixed: 'left', sorter: (a: GMROIItem, b: GMROIItem) => a.sku.localeCompare(b.sku) },
    { title: '产品名称', dataIndex: 'product_name', key: 'product_name', ellipsis: true, sorter: (a: GMROIItem, b: GMROIItem) => a.product_name.localeCompare(b.product_name) },
    { title: '品牌', dataIndex: 'brand', key: 'brand', width: 120, sorter: (a: GMROIItem, b: GMROIItem) => (a.brand || '').localeCompare(b.brand || '') },
    { title: '可售库存', dataIndex: 'available_qty', key: 'available_qty', width: 90, sorter: (a: GMROIItem, b: GMROIItem) => a.available_qty - b.available_qty, render: (v: number) => formatNumber(v) },
    { title: '单位成本', dataIndex: 'unit_cost', key: 'unit_cost', width: 90, render: (v: number) => formatCurrency(v), sorter: (a: GMROIItem, b: GMROIItem) => a.unit_cost - b.unit_cost },
    { title: '库存成本', dataIndex: 'inv_cost', key: 'inv_cost', width: 110, sorter: (a: GMROIItem, b: GMROIItem) => a.inv_cost - b.inv_cost, render: (v: number) => formatCurrencyShort(v) },
    { title: '利润', dataIndex: 'profit', key: 'profit', width: 110, sorter: (a: GMROIItem, b: GMROIItem) => a.profit - b.profit, render: (v: number) => formatCurrencyShort(v) },
    {
      title: 'GMROI', dataIndex: 'gmroi', key: 'gmroi', width: 100,
      sorter: (a: GMROIItem, b: GMROIItem) => (a.gmroi ?? -9999) - (b.gmroi ?? -9999),
      render: (v: number | null) => v === null ? <Text type="secondary">-</Text> : <Text style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 'bold' }}>{v}%</Text>,
    },
    { title: '周转率', dataIndex: 'turnover', key: 'turnover', width: 80, sorter: (a: GMROIItem, b: GMROIItem) => (a.turnover ?? -1) - (b.turnover ?? -1), render: (v: number | null) => v === null ? '-' : v.toFixed(2) },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      sorter: (a: GMROIItem, b: GMROIItem) => a.status.localeCompare(b.status),
      render: (s: string) => <Tag color={statusColors[s]}>{statusText[s]}</Tag>,
    },
  ];

  const intervalColumns = [
    { title: '折扣区间', dataIndex: 'discount_range', key: 'discount_range', width: 120 },
    { title: 'SKU数', dataIndex: 'sku_count', key: 'sku_count', width: 80, sorter: (a: IntervalItem, b: IntervalItem) => a.sku_count - b.sku_count },
    { title: '销售额', dataIndex: 'revenue', key: 'revenue', width: 120, sorter: (a: IntervalItem, b: IntervalItem) => a.revenue - b.revenue, render: (v: number) => formatCurrencyShort(v) },
    { title: '利润', dataIndex: 'profit', key: 'profit', width: 120, sorter: (a: IntervalItem, b: IntervalItem) => a.profit - b.profit, render: (v: number) => formatCurrencyShort(v) },
    { title: '毛利率', dataIndex: 'margin_pct', key: 'margin_pct', width: 90, sorter: (a: IntervalItem, b: IntervalItem) => a.margin_pct - b.margin_pct, render: (v: number) => `${v}%` },
    { title: '单SKU利润', dataIndex: 'avg_profit_per_sku', key: 'avg_profit_per_sku', width: 110, sorter: (a: IntervalItem, b: IntervalItem) => a.avg_profit_per_sku - b.avg_profit_per_sku, render: (v: number) => formatCurrencyShort(v) },
  ];

  // ============================================================
  // Render
  // ============================================================
  const toolbar = (
    <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
      <Space>
        <Select
          value={brand}
          onChange={setBrand}
          options={brandOptions}
          style={{ width: 160 }}
        />
        {activeTab !== 'forecast' && activeTab !== 'cashflow' && activeTab !== 'interval' && (
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 120 }}
            placeholder="选择月份"
          >
            {periods.map(p => (
              <Select.Option key={p.period} value={p.period}>{p.period}</Select.Option>
            ))}
          </Select>
        )}
      </Space>
      <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
        导出Excel
      </Button>
    </Row>
  );

  return (
    <div>
      {toolbar}
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'abc',
          label: 'ABC分类分析',
          children: (
            <Spin spinning={loading}>
              {abcData ? (
                <>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="A类（核心）" value={abcData.summary.a_count} suffix="个SKU"
                          valueStyle={{ color: '#ff4d4f' }} prefix={<CrownOutlined />} />
                        <Text type="secondary">收入占比 {abcData.summary.a_revenue_pct}%</Text>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="B类（重要）" value={abcData.summary.b_count} suffix="个SKU"
                          valueStyle={{ color: '#faad14' }} />
                        <Text type="secondary">收入占比 {abcData.summary.b_revenue_pct}%</Text>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="C类（一般）" value={abcData.summary.c_count} suffix="个SKU"
                          valueStyle={{ color: '#52c41a' }} />
                        <Text type="secondary">收入占比 {abcData.summary.c_revenue_pct}%</Text>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总销售额" value={abcData.summary.total_revenue}
                          formatter={(v) => formatCurrencyShort(v as number)} />
                        <Text type="secondary">总利润 {formatCurrencyShort(abcData.summary.total_profit)}</Text>
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={14}>
                      <Card title="帕累托图（TOP 30 SKU）" size="small">
                        {abcChartOption && <ReactECharts option={abcChartOption} style={{ height: 350 }} />}
                      </Card>
                    </Col>
                    <Col span={10}>
                      <Card title="ABC收入分布" size="small">
                        {abcPieOption && <ReactECharts option={abcPieOption} style={{ height: 350 }} />}
                      </Card>
                    </Col>
                  </Row>
                  <Card title="ABC分类明细" size="small">
                    <Table
                      dataSource={abcData.items}
                      columns={abcColumns}
                      rowKey="sku"
                      size="small"
                      scroll={{ x: 900 }}
                      pagination={standardPagination(20)}
                    />
                  </Card>
                </>
              ) : <Empty description="暂无数据" />}
            </Spin>
          ),
        },
        {
          key: 'gmroi',
          label: 'GMROI库存回报',
          children: (
            <Spin spinning={loading}>
              {gmroiData ? (
                <>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="整体GMROI" value={gmroiData.summary.overall_gmroi} suffix="%"
                          valueStyle={{ color: gmroiData.summary.overall_gmroi > 0 ? '#52c41a' : '#ff4d4f' }}
                          prefix={<DollarOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="总库存成本" value={gmroiData.summary.total_inv_cost}
                          formatter={(v) => formatCurrencyShort(v as number)} prefix={<WalletOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="盈利SKU" value={gmroiData.summary.positive_gmroi_count}
                          suffix={`/ ${gmroiData.summary.total_skus}`}
                          valueStyle={{ color: '#52c41a' }} prefix={<CheckCircleOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="亏损SKU" value={gmroiData.summary.negative_gmroi_count}
                          suffix={`/ ${gmroiData.summary.total_skus}`}
                          valueStyle={{ color: gmroiData.summary.negative_gmroi_count > 0 ? '#ff4d4f' : undefined }}
                          prefix={<WarningOutlined />} />
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={24}>
                      <Card title="GMROI散点图（库存成本 × 回报率）" size="small">
                        {gmroiChartOption && <ReactECharts option={gmroiChartOption} style={{ height: 350 }} />}
                      </Card>
                    </Col>
                  </Row>
                  <Card title="GMROI明细" size="small">
                    <Table
                      dataSource={gmroiData.items}
                      columns={gmroiColumns}
                      rowKey="sku"
                      size="small"
                      scroll={{ x: 1000 }}
                      pagination={standardPagination(20)}
                    />
                  </Card>
                </>
              ) : <Empty description="暂无数据" />}
            </Spin>
          ),
        },
        {
          key: 'forecast',
          label: '销售预测',
          children: (
            <Spin spinning={loading}>
              {forecastData ? (
                <>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="下月预测销售额" value={forecastData.summary.next_month_revenue}
                          formatter={(v) => formatCurrencyShort(v as number)}
                          prefix={forecastData.summary.trend_direction === 'up' ? <RiseOutlined /> : <FallOutlined />}
                          valueStyle={{ color: forecastData.summary.trend_direction === 'up' ? '#52c41a' : '#ff4d4f' }} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="下月预测利润" value={forecastData.summary.next_month_profit}
                          formatter={(v) => formatCurrencyShort(v as number)} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="趋势方向" value={forecastData.summary.trend_direction === 'up' ? '上升' : forecastData.summary.trend_direction === 'down' ? '下降' : '平稳'}
                          valueStyle={{ color: forecastData.summary.trend_direction === 'up' ? '#52c41a' : forecastData.summary.trend_direction === 'down' ? '#ff4d4f' : undefined }}
                          prefix={<LineChartOutlined />} />
                        <Text type="secondary">月均增长 {forecastData.trend.avg_growth_rate}%</Text>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="预测置信度" value={forecastData.summary.confidence === 'high' ? '高' : forecastData.summary.confidence === 'medium' ? '中' : '低'}
                          valueStyle={{ color: forecastData.summary.confidence === 'high' ? '#52c41a' : forecastData.summary.confidence === 'medium' ? '#faad14' : '#ff4d4f' }} />
                        <Text type="secondary">R² = {forecastData.trend.r_squared} | {forecastData.summary.data_points}个数据点</Text>
                      </Card>
                    </Col>
                  </Row>
                  <Card title="销售趋势与预测" size="small" style={{ marginBottom: 16 }}>
                    {forecastChartOption && <ReactECharts option={forecastChartOption} style={{ height: 400 }} />}
                  </Card>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title="预测参数" size="small">
                        <Row gutter={[16, 8]}>
                          <Col span={12}><Text type="secondary">趋势斜率:</Text> <Text strong>{formatCurrencyShort(forecastData.trend.slope)}/月</Text></Col>
                          <Col span={12}><Text type="secondary">截距:</Text> <Text strong>{formatCurrencyShort(forecastData.trend.intercept)}</Text></Col>
                          <Col span={12}><Text type="secondary">利润斜率:</Text> <Text strong>{formatCurrencyShort(forecastData.trend.slope_profit)}/月</Text></Col>
                          <Col span={12}><Text type="secondary">R²拟合度:</Text> <Text strong>{forecastData.trend.r_squared}</Text></Col>
                          <Col span={12}><Text type="secondary">平均环比增长:</Text> <Text strong>{forecastData.trend.avg_growth_rate}%</Text></Col>
                          <Col span={12}><Text type="secondary">数据点数:</Text> <Text strong>{forecastData.summary.data_points}</Text></Col>
                        </Row>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="预测明细" size="small">
                        <Table
                          dataSource={forecastData.forecast}
                          columns={[
                            { title: '月份', dataIndex: 'period', key: 'period' },
                            { title: '预测销售额', dataIndex: 'revenue', key: 'revenue', render: (v: number) => formatCurrencyShort(v) },
                            { title: '预测利润', dataIndex: 'profit', key: 'profit', render: (v: number) => formatCurrencyShort(v) },
                            { title: '预测成本', dataIndex: 'cost', key: 'cost', render: (v: number) => formatCurrencyShort(v) },
                          ]}
                          rowKey="period"
                          size="small"
                          pagination={standardPagination(10)}
                        />
                      </Card>
                    </Col>
                  </Row>
                </>
              ) : <Empty description="暂无数据" />}
            </Spin>
          ),
        },
        {
          key: 'cashflow',
          label: '现金流预测',
          children: (
            <Spin spinning={loading}>
              {cashflowData ? (
                <>
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title="下月现金流入" value={cashflowData.summary.next_month_inflow}
                          formatter={(v) => formatCurrencyShort(v as number)}
                          valueStyle={{ color: '#52c41a' }} prefix={<RiseOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="下月现金流出" value={cashflowData.summary.next_month_outflow}
                          formatter={(v) => formatCurrencyShort(v as number)}
                          valueStyle={{ color: '#ff4d4f' }} prefix={<FallOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="下月净现金流" value={cashflowData.summary.next_month_net}
                          formatter={(v) => formatCurrencyShort(v as number)}
                          valueStyle={{ color: cashflowData.summary.next_month_net >= 0 ? '#52c41a' : '#ff4d4f' }}
                          prefix={<WalletOutlined />} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title="预测期总净流" value={cashflowData.summary.forecast_total_net}
                          formatter={(v) => formatCurrencyShort(v as number)} />
                        <Text type="secondary">月均费用 {formatCurrencyShort(cashflowData.summary.avg_monthly_expense)}</Text>
                      </Card>
                    </Col>
                  </Row>
                  {!cashflowData.has_expense_data && (
                    <Alert
                      message="未导入费用数据，当前费用按利润的15%估算"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  <Row gutter={16}>
                    <Col span={16}>
                      <Card title="现金流预测图" size="small">
                        {cashflowChartOption && <ReactECharts option={cashflowChartOption} style={{ height: 400 }} />}
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card title="月均费用明细" size="small">
                        {cashflowData.expense_breakdown.length > 0 ? (
                          <Table
                            dataSource={cashflowData.expense_breakdown}
                            columns={[
                              { title: '类型', dataIndex: 'type', key: 'type' },
                              { title: '月均', dataIndex: 'monthly_avg', key: 'monthly_avg', render: (v: number) => formatCurrencyShort(v) },
                              { title: '占比', dataIndex: 'pct', key: 'pct', render: (v: number) => `${v}%` },
                            ]}
                            rowKey="type"
                            size="small"
                            pagination={standardPagination(10)}
                          />
                        ) : (
                          <Empty description="无费用数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        )}
                      </Card>
                    </Col>
                  </Row>
                </>
              ) : <Empty description="暂无数据" />}
            </Spin>
          ),
        },
        {
          key: 'interval',
          label: '最优经营区间',
          children: (
            <Spin spinning={loading}>
              {intervalData ? (
                <>
                  {intervalData.optimal && (
                    <Alert
                      message={`最优折扣区间: ${intervalData.optimal.discount_range} — 总利润 ${formatCurrencyShort(intervalData.optimal.profit)}，毛利率 ${intervalData.optimal.margin_pct}%`}
                      type="success"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                  <Card title="不同折扣区间的利润表现" size="small" style={{ marginBottom: 16 }}>
                    {intervalChartOption && <ReactECharts option={intervalChartOption} style={{ height: 350 }} />}
                  </Card>
                  <Card title="区间明细" size="small">
                    <Table
                      dataSource={intervalData.intervals}
                      columns={intervalColumns}
                      rowKey="discount_range"
                      size="small"
                      pagination={standardPagination(10)}
                    />
                  </Card>
                </>
              ) : <Empty description="暂无数据" />}
            </Spin>
          ),
        },
      ]} />
    </div>
  );
}
