import { useEffect, useState, useMemo } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Tag, Segmented, Typography, Space, Alert, Empty, DatePicker } from 'antd';
import {
  ShopOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  TrophyOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { shopDailyApi } from '../api';
import { formatCurrency, formatCurrencyShort, formatNumber } from '../utils/format';

const { Text } = Typography;

type PeriodDays = 7 | 14 | 30;

interface ShopItem { shop: string; count: number; paid: number; paid_pct: number; refund: number; net: number; refund_rate: number; avg_order: number; active_days: number; }
interface SkuItem { sku: string; name: string; qty: number; amount: number; avg_price: number; orders: number; }
interface TrendItem { date: string; orders: number; paid: number; refund: number; net: number; refund_count: number; dod_pct: number | null; refund_full: number; refund_part: number; }
interface Overview {
  range: { start: string; end: string; days: number };
  total_orders: number;
  total_paid: number;
  total_refund: number;
  net_paid: number;
  refund_rate: number;
  refund_count: number;
  avg_daily_paid: number;
  avg_daily_net: number;
  avg_order_value: number;
  active_days: number;
  today: { date: string; orders: number; paid: number; refund: number; net: number };
  yesterday: { date: string; orders: number; paid: number; refund: number; net: number };
  dod_pct: number;
  shops: ShopItem[];
}

export default function ShopDaily() {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<PeriodDays>(7);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [topSkus, setTopSkus] = useState<SkuItem[]>([]);
  const [byShop, setByShop] = useState<ShopItem[]>([]);
  const [shopFilter, setShopFilter] = useState<string>('慕咖');
  const [detailDate, setDetailDate] = useState<string>('');
  const [dailyDetail, setDailyDetail] = useState<{ date: string; found: boolean; order_count?: number; paid?: number; refund?: number; refund_count?: number; net?: number; shops?: { shop: string; count: number; paid: number; refund: number; net: number }[] } | null>(null);

  const loadAll = async (days: number, shop: string) => {
    setLoading(true);
    try {
      const [ov, tr, ts, bs] = await Promise.all([
        shopDailyApi.overview(days, shop),
        shopDailyApi.trend(days, shop),
        shopDailyApi.topSkus(days, shop, 30),
        shopDailyApi.byShop(days, shop),
      ]);
      setOverview(ov.data.data);
      setTrend(tr.data.data);
      setTopSkus(ts.data.data);
      setByShop(bs.data.data);
      // 默认选最新有数据的日期
      const latest = ov.data.data?.range?.end;
      if (latest) {
        setDetailDate(latest);
        const dd = await shopDailyApi.dailyDetail(latest, shop);
        setDailyDetail(dd.data.data);
      }
    } catch (e) {
      console.error('shop-daily load error', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll(period, shopFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, shopFilter]);

  const onDetailDateChange = async (date: string) => {
    setDetailDate(date);
    try {
      const dd = await shopDailyApi.dailyDetail(date, shopFilter);
      setDailyDetail(dd.data.data);
    } catch { /* ignore */ }
  };

  // ── 趋势图 option ──
  const trendOption = useMemo(() => {
    const dates = trend.map((t) => t.date.slice(5));
    const paidData = trend.map((t) => t.paid);
    const refundData = trend.map((t) => t.refund);
    const netData = trend.map((t) => t.net);
    const orderData = trend.map((t) => t.orders);
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: { data: ['成交金额', '退款金额', '净成交', '订单数'], top: 0 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10 } },
      yAxis: [
        { type: 'value', name: '金额', axisLabel: { formatter: (v: number) => formatCurrencyShort(v) } },
        { type: 'value', name: '单数', splitLine: { show: false } },
      ],
      series: [
        { name: '成交金额', type: 'bar', data: paidData, itemStyle: { color: '#1677ff', borderRadius: [3, 3, 0, 0] } },
        { name: '退款金额', type: 'line', data: refundData, smooth: true, itemStyle: { color: '#cf1322' }, lineStyle: { width: 2 } },
        { name: '净成交', type: 'line', data: netData, smooth: true, itemStyle: { color: '#52c41a' }, lineStyle: { width: 2 } },
        { name: '订单数', type: 'line', yAxisIndex: 1, data: orderData, smooth: true, itemStyle: { color: '#fa8c16' }, lineStyle: { width: 1, type: 'dashed' } },
      ],
    };
  }, [trend]);

  // ── 店铺占比饼图 ──
  const shopPieOption = useMemo(() => {
    const data = byShop.map((s) => ({ name: s.shop, value: s.paid }));
    return {
      tooltip: { trigger: 'item', formatter: '{b}<br/>¥{c} ({d}%)' },
      series: [{
        type: 'pie', radius: ['40%', '70%'], data,
        label: { formatter: '{b}\n{d}%', fontSize: 10 },
        color: ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96'],
      }],
    };
  }, [byShop]);

  const trendColumns = [
    { title: '日期', dataIndex: 'date', render: (v: string) => v.slice(5) },
    { title: '订单数', dataIndex: 'orders', align: 'right' as const, sorter: (a: TrendItem, b: TrendItem) => a.orders - b.orders },
    { title: '成交', dataIndex: 'paid', align: 'right' as const, render: (v: number) => formatCurrency(v), sorter: (a: TrendItem, b: TrendItem) => a.paid - b.paid },
    { title: '退款', dataIndex: 'refund', align: 'right' as const, render: (v: number) => v ? <span style={{ color: '#cf1322' }}>-{formatCurrency(v)}</span> : '—', sorter: (a: TrendItem, b: TrendItem) => a.refund - b.refund },
    { title: '净成交', dataIndex: 'net', align: 'right' as const, render: (v: number) => <strong style={{ color: '#3c8436' }}>{formatCurrency(v)}</strong>, sorter: (a: TrendItem, b: TrendItem) => a.net - b.net },
    {
      title: '环比', dataIndex: 'dod_pct', align: 'right' as const,
      render: (v: number | null) => v === null ? '—' : <Tag color={v >= 0 ? 'red' : 'green'}>{v >= 0 ? '+' : ''}{v.toFixed(1)}%</Tag>,
    },
  ];

  const skuColumns = [
    { title: '#', render: (_: unknown, __: unknown, i: number) => i + 1, width: 40 },
    { title: 'SKU', dataIndex: 'sku', render: (v: string) => <code style={{ fontSize: 11 }}>{v}</code> },
    { title: '商品名称', dataIndex: 'name', ellipsis: true },
    { title: '件数', dataIndex: 'qty', align: 'right' as const, render: (v: number) => formatNumber(v) },
    { title: '实付', dataIndex: 'amount', align: 'right' as const, render: (v: number) => <strong>{formatCurrency(v)}</strong>, sorter: (a: SkuItem, b: SkuItem) => a.amount - b.amount },
    { title: '均价', dataIndex: 'avg_price', align: 'right' as const, render: (v: number) => `¥${v.toLocaleString()}` },
    { title: '订单数', dataIndex: 'orders', align: 'right' as const },
  ];

  const shopColumns = [
    { title: '店铺', dataIndex: 'shop' },
    { title: '订单数', dataIndex: 'count', align: 'right' as const, render: (v: number) => formatNumber(v) },
    { title: '成交', dataIndex: 'paid', align: 'right' as const, render: (v: number) => formatCurrency(v) },
    { title: '退款', dataIndex: 'refund', align: 'right' as const, render: (v: number) => v ? <span style={{ color: '#cf1322' }}>-{formatCurrency(v)}</span> : '—' },
    { title: '净成交', dataIndex: 'net', align: 'right' as const, render: (v: number) => <strong style={{ color: '#3c8436' }}>{formatCurrency(v)}</strong> },
    { title: '退款率', dataIndex: 'refund_rate', align: 'right' as const, render: (v: number) => v ? <span style={{ color: v > 30 ? '#cf1322' : undefined }}>{v.toFixed(1)}%</span> : '—' },
    { title: '客单价', dataIndex: 'avg_order', align: 'right' as const, render: (v: number) => `¥${v.toLocaleString()}` },
  ];

  const dodColor = overview?.dod_pct && overview.dod_pct >= 0 ? '#cf1322' : '#3c8436';

  return (
    <Spin spinning={loading}>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="旺店通实时订单数据"
        description="数据源：旺店通API trade_query（订单）+ refund_query（退款）。不含天猫/拼多多订单（平台API限制）。净成交 = 成交金额 − 退款金额。每天凌晨01:30自动同步前一天数据。"
      />

      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col>
          <Segmented
            value={period}
            onChange={(v) => setPeriod(v as PeriodDays)}
            options={[
              { label: '7天', value: 7 },
              { label: '14天', value: 14 },
              { label: '30天', value: 30 },
            ]}
          />
        </Col>
        <Col>
          <Segmented
            value={shopFilter}
            onChange={(v) => setShopFilter(v as string)}
            options={[
              { label: '慕咖', value: '慕咖' },
              { label: '巴恩天然', value: '巴恩' },
              { label: '稻壳', value: '稻壳' },
              { label: '全部', value: '' },
            ]}
          />
        </Col>
      </Row>

      {/* KPI 卡片 */}
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="成交金额" value={overview?.total_paid || 0} prefix={<DollarOutlined />} formatter={(v) => formatCurrencyShort(v as number)} valueStyle={{ color: '#1677ff' }} /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="退款金额" value={overview?.total_refund || 0} prefix="−" formatter={(v) => formatCurrencyShort(v as number)} valueStyle={{ color: '#cf1322' }} suffix={overview?.refund_rate ? <span style={{ fontSize: 12, color: '#999' }}>（{overview.refund_rate}%）</span> : null} /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="净成交" value={overview?.net_paid || 0} formatter={(v) => formatCurrencyShort(v as number)} valueStyle={{ color: '#3c8436' }} /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="总订单" value={overview?.total_orders || 0} prefix={<ShoppingCartOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="日均净成交" value={overview?.avg_daily_net || 0} formatter={(v) => formatCurrencyShort(v as number)} /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="客单价" value={overview?.avg_order_value || 0} prefix="¥" /></Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="今日 vs 昨日"
              value={overview?.dod_pct || 0}
              suffix="%"
              prefix={overview?.dod_pct && overview.dod_pct >= 0 ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{ color: dodColor, fontSize: 22 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small"><Statistic title="今日净成交" value={overview?.today?.net || 0} prefix={<ShopOutlined />} formatter={(v) => formatCurrencyShort(v as number)} /></Card>
        </Col>
      </Row>

      {/* 趋势图 */}
      <Card size="small" style={{ marginBottom: 12 }} title="每日趋势">
        {trend.length > 0 ? (
          <ReactECharts option={trendOption} style={{ height: 280 }} />
        ) : <Empty description="暂无趋势数据" />}
      </Card>

      {/* 店铺占比 + Top SKU */}
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col xs={24} lg={10}>
          <Card size="small" title="店铺占比">
            {byShop.length > 0 ? (
              <>
                <ReactECharts option={shopPieOption} style={{ height: 200 }} />
                <Table
                  size="small"
                  rowKey="shop"
                  columns={shopColumns}
                  dataSource={byShop}
                  pagination={false}
                  style={{ marginTop: 8 }}
                />
              </>
            ) : <Empty />}
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card size="small" title={<Space><TrophyOutlined />Top 30 SKU</Space>}>
            <Table
              size="small"
              rowKey="sku"
              columns={skuColumns}
              dataSource={topSkus}
              pagination={{ pageSize: 10, size: 'small' }}
              scroll={{ x: 500 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 日明细 */}
      <Card size="small" title="日明细" extra={
        <DatePicker
          value={detailDate ? dayjs(detailDate) : null}
          onChange={(d) => d && onDetailDateChange(d.format('YYYY-MM-DD'))}
          allowClear={false}
          size="small"
        />
      }>
        {dailyDetail?.found ? (
          <Row gutter={[8, 8]}>
            <Col span={4}><Statistic title="订单数" value={dailyDetail.order_count || 0} /></Col>
            <Col span={4}><Statistic title="成交金额" value={dailyDetail.paid || 0} formatter={(v) => formatCurrencyShort(v as number)} /></Col>
            <Col span={4}><Statistic title="退款金额" value={dailyDetail.refund || 0} valueStyle={{ color: '#cf1322' }} formatter={(v) => formatCurrencyShort(v as number)} suffix={dailyDetail.refund_count ? <span style={{ fontSize: 12, color: '#999' }}>（{dailyDetail.refund_count}单）</span> : null} /></Col>
            <Col span={4}><Statistic title="净成交" value={dailyDetail.net || 0} valueStyle={{ color: '#3c8436' }} formatter={(v) => formatCurrencyShort(v as number)} /></Col>
            <Col span={8}>
              <Table
                size="small"
                rowKey="shop"
                columns={[
                  { title: '店铺', dataIndex: 'shop' },
                  { title: '订单数', dataIndex: 'count', align: 'right' as const },
                  { title: '成交', dataIndex: 'paid', align: 'right' as const, render: (v: number) => formatCurrency(v) },
                  { title: '退款', dataIndex: 'refund', align: 'right' as const, render: (v: number) => v ? <span style={{ color: '#cf1322' }}>-{formatCurrency(v)}</span> : '—' },
                  { title: '净成交', dataIndex: 'net', align: 'right' as const, render: (v: number) => <strong style={{ color: '#3c8436' }}>{formatCurrency(v)}</strong> },
                ]}
                dataSource={dailyDetail.shops || []}
                pagination={false}
              />
            </Col>
          </Row>
        ) : <Empty description="该日期无数据" />}
      </Card>
    </Spin>
  );
}
