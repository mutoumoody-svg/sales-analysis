import { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Tag, Segmented, Progress, List, Typography, Space, Alert, Select } from 'antd';
import {
  ArrowUpOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  ShopOutlined,
  RollbackOutlined,
  TrophyOutlined,
  WarningOutlined,
  BulbOutlined,
  MedicineBoxOutlined,
  SafetyCertificateOutlined,
  FundOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { salesApi, dashboardApi } from '../api';
import { usePeriods } from '../hooks/usePeriods';
import type {
  OverviewData,
  DailyTrendItem,
  PlatformSales,
  StoreSales,
  ProductSales,
  HealthIndex,
  CeoReport,
} from '../types';
import { formatCurrency, formatCurrencyShort, formatNumber, formatPercent } from '../utils/format';

type BrandType = '全部' | '慕咖STTOKE' | '慕咖（MOODY）' | 'MoodyCoffee' | '巴恩天然';

const brandOptions: { label: string; value: BrandType }[] = [
  { label: '全部品牌', value: '全部' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

const { Text } = Typography;

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [brand, setBrand] = useState<BrandType>('全部');
  const { periods, month, setMonth } = usePeriods();
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [trend, setTrend] = useState<DailyTrendItem[]>([]);
  const [platforms, setPlatforms] = useState<PlatformSales[]>([]);
  const [stores, setStores] = useState<StoreSales[]>([]);
  const [products, setProducts] = useState<ProductSales[]>([]);
  const [health, setHealth] = useState<HealthIndex | null>(null);
  const [ceoReport, setCeoReport] = useState<CeoReport | null>(null);

  const loadData = useCallback((selectedBrand: BrandType, selectedMonth: string) => {
    if (!selectedMonth) return;
    setLoading(true);
    const brandParams = selectedBrand === '全部' ? {} : { brand: selectedBrand };
    const params = { ...brandParams, month: selectedMonth };
    Promise.all([
      salesApi.overview(params),
      salesApi.dailyTrend(params),
      salesApi.byPlatform(params),
      salesApi.byStore({ ...params, limit: 10 }),
      salesApi.byProduct({ ...params, limit: 10 }),
      dashboardApi.healthIndex(params),
      dashboardApi.ceoReport(params),
    ])
      .then(([ov, tr, pf, st, pr, hi, ceo]) => {
        setOverview(ov.data.data);
        setTrend(tr.data.data.daily);
        setPlatforms(pf.data.data.platforms);
        setStores(st.data.data.stores);
        setProducts(pr.data.data.products);
        setHealth(hi.data.data);
        setCeoReport(ceo.data.data);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData(brand, month);
  }, [brand, month, loadData]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', padding: 100 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 日趋势图配置
  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['销售额', '毛利'], top: 0 },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      boundaryGap: false,
      data: trend.map((d) => d.date),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => formatCurrencyShort(v) } },
    series: [
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#1677ff' },
        data: trend.map((d) => d.revenue),
      },
      {
        name: '毛利',
        type: 'line',
        smooth: true,
        itemStyle: { color: '#52c41a' },
        data: trend.map((d) => d.gross_profit),
      },
    ],
  };

  // 平台占比饼图
  const platformOption = {
    tooltip: { trigger: 'item' as const, formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, type: 'scroll' as const },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
        data: platforms
          .filter((p) => p.total_revenue > 0)
          .map((p) => ({ name: p.platform, value: Math.round(p.total_revenue) })),
      },
    ],
  };

  // 店铺排名柱状图
  const storeOption = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: Array<{ dataIndex: number }>) => {
        const idx = params[0]?.dataIndex;
        if (idx === undefined) return '';
        const s = stores[idx];
        if (!s) return '';
        return `${s.store_name}<br/>
          实际销售额: ¥${formatNumber(s.total_revenue)}<br/>
          发货金额: ¥${formatNumber(s.ship_amount)}<br/>
          退货金额: ¥${formatNumber(s.return_amount)}<br/>
          退货率: ${s.return_rate}%<br/>
          实际成本: ¥${formatNumber(s.total_cost)}<br/>
          实际利润: ¥${formatNumber(s.gross_profit)}`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' as const, axisLabel: { formatter: (v: number) => formatCurrencyShort(v) } },
    yAxis: {
      type: 'category' as const,
      data: stores.map((s) => s.store_name).reverse(),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: stores.map((s) => Math.round(s.total_revenue)).reverse(),
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#1677ff' },
              { offset: 1, color: '#69b1ff' },
            ],
          },
          borderRadius: [0, 4, 4, 0],
        },
        label: { show: true, position: 'right' as const, formatter: (p: { value: number }) => formatCurrencyShort(p.value), fontSize: 10 },
      },
    ],
  };

  // 健康指数雷达图
  const healthRadarOption = health ? {
    tooltip: {},
    radar: {
      indicator: [
        { name: '利润健康', max: 100 },
        { name: '销售健康', max: 100 },
        { name: '库存健康', max: 100 },
      ],
      shape: 'polygon',
      radius: '65%',
      axisName: { color: '#666', fontSize: 13 },
      splitArea: { areaStyle: { color: ['rgba(114,46,209,0.02)', 'rgba(114,46,209,0.05)', 'rgba(114,46,209,0.08)', 'rgba(114,46,209,0.12)'] } },
      splitLine: { lineStyle: { color: '#e8e8e8' } },
      axisLine: { lineStyle: { color: '#e8e8e8' } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: [health.profit_health, health.sales_health, health.inventory_health],
        name: '健康指数',
        areaStyle: { color: 'rgba(114,46,209,0.2)' },
        lineStyle: { color: '#722ed1', width: 2 },
        itemStyle: { color: '#722ed1' },
      }],
    }],
  } : {};

  const productColumns = [
    { title: '排名', render: (_: unknown, __: unknown, i: number) => i + 1, width: 60 },
    { title: 'SKU', dataIndex: 'sku', width: 120 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '发货量', dataIndex: 'ship_qty', width: 80, render: (v: number) => formatNumber(v) },
    { title: '退货量', dataIndex: 'return_qty', width: 80, render: (v: number) => v > 0 ? <Tag color="red">{formatNumber(v)}</Tag> : formatNumber(v) },
    { title: '实际销量', dataIndex: 'total_qty', width: 80, render: (v: number) => formatNumber(v) },
    { title: '实际销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ProductSales, b: ProductSales) => a.total_revenue - b.total_revenue },
    { title: '实际成本', dataIndex: 'total_cost', width: 120, render: (v: number) => <span style={{ color: '#ff4d4f' }}>{formatCurrency(v)}</span> },
    { title: '实际利润', dataIndex: 'gross_profit', width: 120, render: (v: number) => <span style={{ color: '#52c41a' }}>{formatCurrency(v)}</span> },
    { title: '利润率', dataIndex: 'gross_margin_pct', width: 90, render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag> },
  ];

  const gradeColor = (g: string) => {
    if (g === 'A') return '#52c41a';
    if (g === 'B') return '#73d13d';
    if (g === 'C') return '#faad14';
    if (g === 'D') return '#fa8c16';
    return '#ff4d4f';
  };

  const healthScoreColor = (s: number) => s >= 80 ? '#52c41a' : s >= 60 ? '#fa8c16' : '#ff4d4f';

  const priorityConfig: Record<string, { color: string; icon: React.ReactNode }> = {
    high: { color: '#ff4d4f', icon: <WarningOutlined style={{ color: '#ff4d4f' }} /> },
    medium: { color: '#fa8c16', icon: <WarningOutlined style={{ color: '#fa8c16' }} /> },
    low: { color: '#1677ff', icon: <BulbOutlined style={{ color: '#1677ff' }} /> },
  };

  return (
    <div className="page-container">
      {/* 品牌切换器 + 月份选择器 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Segmented options={brandOptions} value={brand} onChange={(v) => setBrand(v as BrandType)} size="large" />
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 140 }}
            size="large"
            options={periods.map((p) => ({
              label: `${p.period}（¥${(p.net_revenue / 10000).toFixed(1)}万）`,
              value: p.period,
            }))}
            placeholder="选择月份"
          />
        </Space>
        <div style={{ fontSize: 13, color: '#999' }}>
          数据周期: {overview?.date_range.start} ~ {overview?.date_range.end}
        </div>
      </div>

      {/* 企业健康指数 + CEO日报 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title={<span><SafetyCertificateOutlined style={{ marginRight: 8, color: '#722ed1' }} />企业健康指数</span>}>
            {health && (
              <>
                <Row gutter={[8, 8]} align="middle">
                  <Col span={10} style={{ textAlign: 'center' }}>
                    <Progress
                      type="dashboard"
                      percent={health.overall_score}
                      size={140}
                      strokeColor={gradeColor(health.grade)}
                      format={() => (
                        <div>
                          <div style={{ fontSize: 32, fontWeight: 700, color: gradeColor(health.grade) }}>{health.overall_score}</div>
                          <div style={{ fontSize: 20, fontWeight: 700, color: gradeColor(health.grade) }}>{health.grade}</div>
                        </div>
                      )}
                    />
                  </Col>
                  <Col span={14}>
                    <ReactECharts option={healthRadarOption} style={{ height: 160 }} />
                  </Col>
                </Row>
                <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <Progress type="circle" percent={health.profit_health} size={56} strokeColor={healthScoreColor(health.profit_health)} format={(p) => <span style={{ fontSize: 12 }}>{p}</span>} />
                    <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                      <FundOutlined /> 利润健康
                    </div>
                  </Col>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <Progress type="circle" percent={health.sales_health} size={56} strokeColor={healthScoreColor(health.sales_health)} format={(p) => <span style={{ fontSize: 12 }}>{p}</span>} />
                    <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                      <ShoppingCartOutlined /> 销售健康
                    </div>
                  </Col>
                  <Col span={8} style={{ textAlign: 'center' }}>
                    <Progress type="circle" percent={health.inventory_health} size={56} strokeColor={healthScoreColor(health.inventory_health)} format={(p) => <span style={{ fontSize: 12 }}>{p}</span>} />
                    <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                      <MedicineBoxOutlined /> 库存健康
                    </div>
                  </Col>
                </Row>
                <div style={{ marginTop: 12, padding: 10, background: '#f6f8fa', borderRadius: 8, fontSize: 12, color: '#666' }}>
                  毛利率 {health.metrics.gross_margin}% · 退货率 {health.metrics.return_rate}% · 缺货 {health.metrics.stockout_count}个SKU
                </div>
              </>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title={<span><BulbOutlined style={{ marginRight: 8, color: '#fa8c16' }} />经营日报</span>}>
            {ceoReport && (
              <>
                {/* 核心数据条 */}
                <Row gutter={[12, 8]} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Statistic title="销售额" value={ceoReport.summary.revenue} prefix="¥" precision={0} valueStyle={{ fontSize: 18, color: '#1677ff' }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="利润" value={ceoReport.summary.profit} prefix="¥" precision={0} valueStyle={{ fontSize: 18, color: '#52c41a' }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="毛利率" value={ceoReport.summary.gross_margin} suffix="%" precision={1} valueStyle={{ fontSize: 18 }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="退货率" value={ceoReport.summary.return_rate} suffix="%" precision={1} valueStyle={{ fontSize: 18, color: ceoReport.summary.return_rate > 10 ? '#ff4d4f' : '#666' }} />
                  </Col>
                </Row>

                {/* 机会 */}
                {ceoReport.opportunities.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6, color: '#52c41a' }}>
                      <TrophyOutlined style={{ marginRight: 6 }} />最大机会
                    </div>
                    {ceoReport.opportunities.map((opp, i) => {
                      const cfg = priorityConfig[opp.priority] || priorityConfig.medium;
                      return (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 4, background: '#f6ffed', borderLeft: `3px solid ${cfg.color}`, borderRadius: 4 }}>
                          <Text strong style={{ fontSize: 13 }}>{cfg.icon} {opp.title}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{opp.detail}</Text>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 风险 */}
                {ceoReport.risks.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6, color: '#ff4d4f' }}>
                      <WarningOutlined style={{ marginRight: 6 }} />最大风险
                    </div>
                    {ceoReport.risks.map((risk, i) => {
                      const cfg = priorityConfig[risk.priority] || priorityConfig.medium;
                      return (
                        <div key={i} style={{ padding: '8px 12px', marginBottom: 4, background: '#fff2f0', borderLeft: `3px solid ${cfg.color}`, borderRadius: 4 }}>
                          <Text strong style={{ fontSize: 13 }}>{cfg.icon} {risk.title}</Text>
                          <br />
                          <Text type="secondary" style={{ fontSize: 12 }}>{risk.detail}</Text>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 建议动作 */}
                <div>
                  <div style={{ fontWeight: 600, marginBottom: 6, color: '#1677ff' }}>
                    <BulbOutlined style={{ marginRight: 6 }} />建议动作
                  </div>
                  {ceoReport.actions.map((action, i) => (
                    <div key={i} style={{ padding: '6px 12px', marginBottom: 4, fontSize: 13, color: '#333' }}>
                      <span style={{ color: '#1677ff', marginRight: 8 }}>{i + 1}.</span>
                      {action}
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* 核心指标卡片 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={12} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic title="实际销售额" value={overview?.total_revenue || 0} precision={2} prefix="¥" valueStyle={{ color: '#1677ff' }} />
            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
              发货总额 ¥{formatNumber(overview?.total_ship_amount || 0)}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic title="实际利润" value={overview?.gross_profit || 0} precision={2} prefix="¥" valueStyle={{ color: '#52c41a' }} />
            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
              实际成本 ¥{formatNumber(overview?.total_cost || 0)}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic title="退货金额" value={overview?.return_amount || 0} precision={2} prefix="¥" valueStyle={{ color: '#ff4d4f' }} prefix={<RollbackOutlined />} />
            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
              退货率 {overview?.return_rate || 0}%
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic title="利润率" value={overview?.gross_margin_pct || 0} precision={2} suffix="%" prefix={<ArrowUpOutlined />} valueStyle={{ color: '#fa8c16' }} />
            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
              订单数 {formatNumber(overview?.order_count || 0)}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 次级指标 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={12} md={6}>
          <Card size="small"><Statistic title="店铺数" value={overview?.store_count || 0} prefix={<ShopOutlined />} /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small"><Statistic title="商品数" value={overview?.product_count || 0} prefix={<DollarOutlined />} /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small"><Statistic title="佣金成本" value={overview?.commission_cost || 0} precision={2} prefix="¥" /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small"><Statistic title="当前品牌" value={brand} /></Card>
        </Col>
      </Row>

      {/* 图表区 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="日销售趋势" className="chart-card">
            <ReactECharts option={trendOption} style={{ height: 320 }} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="平台销售占比（实际销售额）" className="chart-card">
            <ReactECharts option={platformOption} style={{ height: 320 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="店铺销售排名 TOP 10（实际销售额）" className="chart-card">
            <ReactECharts option={storeOption} style={{ height: 360 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="商品销售 TOP 10（扣除退货后）" className="chart-card">
            <Table dataSource={products} columns={productColumns} rowKey="product_id" size="small" pagination={false} scroll={{ y: 300, x: 800 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
