import { useEffect, useState, useMemo } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Tag, Segmented, DatePicker, Typography, Space, Alert, Empty } from 'antd';
import {
  ThunderboltOutlined,
  ShoppingCartOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  ShopOutlined,
  InboxOutlined,
  TrophyOutlined,
  CalendarOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import { realtimeApi } from '../api';
import { standardPagination, numberSorter, stringSorter } from '../utils/tableConfig';
import type {
  RealtimeOverview,
  RealtimeTrendItem,
  RealtimeTopSku,
  RealtimeByShop,
  RealtimeByWarehouse,
  RealtimeDailyDetail,
  RealtimeMonthlyItem,
} from '../types';
import { formatCurrency, formatCurrencyShort, formatNumber, formatPercent } from '../utils/format';

const { Text } = Typography;
const { RangePicker } = DatePicker;

type PeriodDays = 7 | 14 | 30;

export default function RealTimeSales() {
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<PeriodDays>(7);
  const [overview, setOverview] = useState<RealtimeOverview | null>(null);
  const [trend, setTrend] = useState<RealtimeTrendItem[]>([]);
  const [topSkus, setTopSkus] = useState<RealtimeTopSku[]>([]);
  const [byShop, setByShop] = useState<RealtimeByShop[]>([]);
  const [byWarehouse, setByWarehouse] = useState<RealtimeByWarehouse[]>([]);
  const [monthly, setMonthly] = useState<RealtimeMonthlyItem[]>([]);
  const [dailyDetail, setDailyDetail] = useState<RealtimeDailyDetail | null>(null);
  const [detailDate, setDetailDate] = useState<string>('');

  // 加载概览+趋势+Top+店铺+仓库
  const loadAll = async (days: number) => {
    setLoading(true);
    try {
      const [ov, tr, ts, bs, bw, ms] = await Promise.all([
        realtimeApi.overview(days),
        realtimeApi.trend(days),
        realtimeApi.topSkus(days, 30),
        realtimeApi.byShop(days),
        realtimeApi.byWarehouse(days),
        realtimeApi.monthlySummary(),
      ]);
      setOverview(ov.data.data);
      setTrend(tr.data.data);
      setTopSkus(ts.data.data);
      setByShop(bs.data.data);
      setByWarehouse(bw.data.data);
      setMonthly(ms.data.data);

      // 默认选最新有数据的日期
      const latest = ov.data.data?.latest_date;
      if (latest && detailDate === '') {
        setDetailDate(latest);
        const dd = await realtimeApi.dailyDetail(latest);
        setDailyDetail(dd.data.data);
      }
    } catch (e) {
      console.error('realtime load error', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll(period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period]);

  // 加载某日明细
  const loadDailyDetail = async (date: string) => {
    if (!date) return;
    try {
      const dd = await realtimeApi.dailyDetail(date);
      setDailyDetail(dd.data.data);
      setDetailDate(date);
    } catch (e) {
      console.error('daily detail error', e);
    }
  };

  // 趋势图配置
  const trendOption = useMemo(() => {
    if (!trend.length) return {};
    const dates = trend.map((t) => t.date.slice(5)); // MM-DD
    const sellData = trend.map((t) => t.sell_amount);
    const costData = trend.map((t) => t.cost_amount);
    const profitData = trend.map((t) => t.gross_profit);
    const marginData = trend.map((t) => t.margin_pct);
    const orderData = trend.map((t) => t.orders);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any[]) => {
          const idx = params[0]?.dataIndex ?? 0;
          const item = trend[idx];
          if (!item) return '';
          return `<div style="font-weight:600;margin-bottom:4px">${item.date}</div>
            <div>销售额: <b>${formatCurrency(item.sell_amount)}</b></div>
            <div>成本: ${formatCurrency(item.cost_amount)}</div>
            <div>毛利: <b style="color:#52c41a">${formatCurrency(item.gross_profit)}</b></div>
            <div>毛利率: ${item.margin_pct}%</div>
            <div>订单: ${item.orders} 单 / ${formatNumber(item.quantity)} 件</div>`;
        },
      },
      legend: {
        data: ['销售额', '成本', '毛利', '毛利率'],
        top: 0,
      },
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
      yAxis: [
        { type: 'value', name: '金额', axisLabel: { formatter: (v: number) => v >= 10000 ? `${(v / 10000).toFixed(0)}万` : `${v}` } },
        { type: 'value', name: '毛利率%', axisLabel: { formatter: '{value}%' }, max: 100 },
      ],
      series: [
        { name: '销售额', type: 'bar', data: sellData, itemStyle: { color: '#1890ff' }, barWidth: '40%' },
        { name: '成本', type: 'bar', data: costData, itemStyle: { color: '#faad14' }, barWidth: '40%' },
        { name: '毛利', type: 'bar', data: profitData, itemStyle: { color: '#52c41a' }, barWidth: '40%' },
        { name: '毛利率', type: 'line', yAxisIndex: 1, data: marginData, itemStyle: { color: '#722ed1' }, lineStyle: { width: 2 }, smooth: true },
      ],
    };
  }, [trend]);

  // 店铺饼图
  const shopChartOption = useMemo(() => {
    if (!byShop.length) return {};
    const top5 = byShop.slice(0, 8);
    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `${p.name}<br/>销售额: <b>${formatCurrency(p.value)}</b><br/>占比: ${p.percent}%`,
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '50%'],
        data: top5.map((s) => ({ name: s.shop, value: s.sell_amount })),
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      }],
    };
  }, [byShop]);

  // 日明细表格列
  const detailColumns = [
    {
      title: 'SKU',
      dataIndex: 'spec_no',
      key: 'spec_no',
      width: 130,
      sorter: stringSorter('spec_no'),
      fixed: 'left' as const,
    },
    {
      title: '商品名称',
      dataIndex: 'goods_name',
      key: 'goods_name',
      sorter: stringSorter('goods_name'),
      ellipsis: true,
    },
    {
      title: '出库量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 90,
      align: 'right' as const,
      sorter: numberSorter('quantity'),
      render: (v: number) => formatNumber(v),
    },
    {
      title: '销售额',
      dataIndex: 'total_sell_amount',
      key: 'total_sell_amount',
      width: 110,
      align: 'right' as const,
      sorter: numberSorter('total_sell_amount'),
      render: (v: number) => <Text strong>{formatCurrency(v)}</Text>,
    },
    {
      title: '成本',
      dataIndex: 'total_cost_amount',
      key: 'total_cost_amount',
      width: 100,
      align: 'right' as const,
      sorter: numberSorter('total_cost_amount'),
      render: (v: number) => formatCurrency(v),
    },
    {
      title: '毛利',
      dataIndex: '_gross',
      key: '_gross',
      width: 100,
      align: 'right' as const,
      render: (_: any, r: any) => {
        const gross = r.total_sell_amount - r.total_cost_amount;
        const pct = r.total_sell_amount > 0 ? (gross / r.total_sell_amount * 100) : 0;
        return <Text style={{ color: gross >= 0 ? '#52c41a' : '#f5222d' }}>{formatCurrency(gross)} ({pct.toFixed(1)}%)</Text>;
      },
    },
    {
      title: '均价',
      dataIndex: 'avg_sell_price',
      key: 'avg_sell_price',
      width: 80,
      align: 'right' as const,
      sorter: numberSorter('avg_sell_price'),
      render: (v: number) => v > 0 ? `¥${v.toFixed(2)}` : <Tag>赠品</Tag>,
    },
    {
      title: '订单数',
      dataIndex: 'order_count',
      key: 'order_count',
      width: 80,
      align: 'right' as const,
      sorter: numberSorter('order_count'),
    },
    {
      title: '店铺',
      dataIndex: 'shops',
      key: 'shops',
      width: 200,
      render: (shops: string[]) => shops?.map((s) => <Tag key={s} style={{ marginBottom: 2 }}>{s}</Tag>),
    },
  ];

  // Top SKU 表格列
  const topSkuColumns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: any, __: any, idx: number) => idx + 1,
    },
    {
      title: 'SKU',
      dataIndex: 'spec_no',
      key: 'spec_no',
      width: 130,
      sorter: stringSorter('spec_no'),
    },
    {
      title: '商品名称',
      dataIndex: 'goods_name',
      key: 'goods_name',
      sorter: stringSorter('goods_name'),
      ellipsis: true,
    },
    {
      title: '出库量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 90,
      align: 'right' as const,
      sorter: numberSorter('quantity'),
      render: (v: number) => formatNumber(v),
    },
    {
      title: '销售额',
      dataIndex: 'sell_amount',
      key: 'sell_amount',
      width: 110,
      align: 'right' as const,
      sorter: numberSorter('sell_amount'),
      render: (v: number) => <Text strong style={{ color: '#1890ff' }}>{formatCurrency(v)}</Text>,
    },
    {
      title: '毛利',
      dataIndex: 'gross_profit',
      key: 'gross_profit',
      width: 110,
      align: 'right' as const,
      sorter: numberSorter('gross_profit'),
      render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#f5222d' }}>{formatCurrency(v)}</Text>,
    },
    {
      title: '毛利率',
      dataIndex: 'margin_pct',
      key: 'margin_pct',
      width: 80,
      align: 'right' as const,
      sorter: numberSorter('margin_pct'),
      render: (v: number) => v > 0 ? `${v.toFixed(1)}%` : '-',
    },
    {
      title: '订单数',
      dataIndex: 'order_count',
      key: 'order_count',
      width: 80,
      align: 'right' as const,
      sorter: numberSorter('order_count'),
    },
    {
      title: '销售天数',
      dataIndex: 'days_sold',
      key: 'days_sold',
      width: 80,
      align: 'center' as const,
      sorter: numberSorter('days_sold'),
      render: (v: number) => <Tag color={v === period ? 'green' : 'blue'}>{v}/{period}</Tag>,
    },
  ];

  // 店铺表格列
  const shopColumns = [
    { title: '店铺', dataIndex: 'shop', key: 'shop', sorter: stringSorter('shop'), ellipsis: true },
    { title: '销售额', dataIndex: 'sell_amount', key: 'sell_amount', width: 110, align: 'right' as const, sorter: numberSorter('sell_amount'), render: (v: number) => <Text strong>{formatCurrency(v)}</Text> },
    { title: '毛利', dataIndex: 'gross_profit', key: 'gross_profit', width: 110, align: 'right' as const, sorter: numberSorter('gross_profit'), render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#f5222d' }}>{formatCurrency(v)}</Text> },
    { title: '毛利率', dataIndex: 'margin_pct', key: 'margin_pct', width: 80, align: 'right' as const, sorter: numberSorter('margin_pct'), render: (v: number) => v > 0 ? `${v.toFixed(1)}%` : '-' },
    { title: '出库量', dataIndex: 'quantity', key: 'quantity', width: 90, align: 'right' as const, sorter: numberSorter('quantity'), render: (v: number) => formatNumber(v) },
    { title: '订单数', dataIndex: 'order_count', key: 'order_count', width: 80, align: 'right' as const, sorter: numberSorter('order_count') },
    { title: 'SKU数', dataIndex: 'sku_count', key: 'sku_count', width: 80, align: 'right' as const, sorter: numberSorter('sku_count') },
  ];

  // 仓库表格列
  const warehouseColumns = [
    { title: '仓库', dataIndex: 'warehouse', key: 'warehouse', sorter: stringSorter('warehouse') },
    { title: '销售额', dataIndex: 'sell_amount', key: 'sell_amount', width: 110, align: 'right' as const, sorter: numberSorter('sell_amount'), render: (v: number) => <Text strong>{formatCurrency(v)}</Text> },
    { title: '毛利', dataIndex: 'gross_profit', key: 'gross_profit', width: 110, align: 'right' as const, sorter: numberSorter('gross_profit'), render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#f5222d' }}>{formatCurrency(v)}</Text> },
    { title: '出库量', dataIndex: 'quantity', key: 'quantity', width: 90, align: 'right' as const, sorter: numberSorter('quantity'), render: (v: number) => formatNumber(v) },
    { title: '订单数', dataIndex: 'order_count', key: 'order_count', width: 80, align: 'right' as const, sorter: numberSorter('order_count') },
    { title: 'SKU数', dataIndex: 'sku_count', key: 'sku_count', width: 80, align: 'right' as const, sorter: numberSorter('sku_count') },
  ];

  // 月度表格列
  const monthlyColumns = [
    { title: '月份', dataIndex: 'month', key: 'month', width: 100, sorter: stringSorter('month') },
    { title: '销售额', dataIndex: 'sell_amount', key: 'sell_amount', width: 130, align: 'right' as const, sorter: numberSorter('sell_amount'), render: (v: number) => <Text strong style={{ color: '#1890ff' }}>{formatCurrency(v)}</Text> },
    { title: '毛利', dataIndex: 'gross_profit', key: 'gross_profit', width: 120, align: 'right' as const, sorter: numberSorter('gross_profit'), render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#f5222d' }}>{formatCurrency(v)}</Text> },
    { title: '毛利率', dataIndex: 'margin_pct', key: 'margin_pct', width: 90, align: 'right' as const, sorter: numberSorter('margin_pct'), render: (v: number) => v > 0 ? `${v.toFixed(1)}%` : '-' },
    { title: '订单数', dataIndex: 'orders', key: 'orders', width: 90, align: 'right' as const, sorter: numberSorter('orders') },
    { title: '出库量', dataIndex: 'quantity', key: 'quantity', width: 100, align: 'right' as const, sorter: numberSorter('quantity'), render: (v: number) => formatNumber(v) },
    { title: '应收', dataIndex: 'receivable', key: 'receivable', width: 120, align: 'right' as const, sorter: numberSorter('receivable'), render: (v: number) => formatCurrency(v) },
    { title: '日均销售', dataIndex: 'avg_daily_sell', key: 'avg_daily_sell', width: 110, align: 'right' as const, sorter: numberSorter('avg_daily_sell'), render: (v: number) => formatCurrency(v) },
    { title: '数据天数', dataIndex: 'days_with_data', key: 'days_with_data', width: 90, align: 'center' as const, sorter: numberSorter('days_with_data') },
  ];

  if (loading && !overview) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载实时数据中..." />
      </div>
    );
  }

  const today = overview?.today;
  const yesterday = overview?.yesterday;
  const periodData = overview?.period;
  const todayVsYesterdaySell = today && yesterday ? yesterday.sell_amount > 0 ? ((today.sell_amount - yesterday.sell_amount) / yesterday.sell_amount * 100) : 0 : 0;

  return (
    <div>
      {/* 头部控制 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <Space>
          <ThunderboltOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <Text strong style={{ fontSize: 16 }}>实时销售分析</Text>
          {overview?.latest_date && (
            <Tag color="green">数据更新至 {overview.latest_date}</Tag>
          )}
        </Space>
        <Space>
          <Segmented
            value={period}
            onChange={(v) => setPeriod(v as PeriodDays)}
            options={[
              { label: '近7天', value: 7 },
              { label: '近14天', value: 14 },
              { label: '近30天', value: 30 },
            ]}
          />
          <ReloadOutlined
            style={{ fontSize: 16, cursor: 'pointer', color: '#1890ff' }}
            onClick={() => loadAll(period)}
          />
        </Space>
      </div>

      {/* 数据源说明 */}
      <Alert
        type="info"
        showIcon
        icon={<ThunderboltOutlined />}
        message="数据来源：旺店通开放API实时出库单（kucun系统每日22:00自动拉取）"
        description="展示已发货出库单的实时数据，含销售额、成本、毛利、店铺、仓库等维度。当天数据可能不完整（取决于拉取时间）。"
        style={{ marginBottom: 16 }}
      />

      {/* KPI 卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="今日销售额"
              value={today?.sell_amount || 0}
              prefix="¥"
              precision={2}
              valueStyle={{ color: today?.sell_amount ? '#1890ff' : '#999' }}
            />
            <div style={{ marginTop: 4, fontSize: 12 }}>
              {today?.has_data ? (
                <Text type="secondary">
                  {today.orders} 单 / {formatNumber(today.quantity)} 件
                </Text>
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="昨日销售额"
              value={yesterday?.sell_amount || 0}
              prefix="¥"
              precision={2}
              valueStyle={{ color: yesterday?.sell_amount ? '#52c41a' : '#999' }}
            />
            <div style={{ marginTop: 4, fontSize: 12 }}>
              {yesterday?.has_data ? (
                <Space size={4}>
                  <Text type="secondary">{yesterday.orders} 单</Text>
                  {todayVsYesterdaySell !== 0 && (
                    <Text style={{ color: todayVsYesterdaySell > 0 ? '#f5222d' : '#52c41a', fontSize: 11 }}>
                      {todayVsYesterdaySell > 0 ? '↑' : '↓'} {Math.abs(todayVsYesterdaySell).toFixed(1)}%
                    </Text>
                  )}
                </Space>
              ) : (
                <Text type="secondary">暂无数据</Text>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={`近${period}天销售额`}
              value={periodData?.sell_amount || 0}
              prefix="¥"
              precision={0}
              valueStyle={{ color: '#722ed1' }}
            />
            <div style={{ marginTop: 4, fontSize: 12 }}>
              <Text type="secondary">
                日均 {formatCurrencyShort(periodData?.avg_daily_sell || 0)} · {periodData?.orders || 0} 单
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={`近${period}天毛利`}
              value={periodData?.gross_profit || 0}
              prefix="¥"
              precision={0}
              valueStyle={{ color: periodData?.gross_profit && periodData.gross_profit > 0 ? '#52c41a' : '#999' }}
            />
            <div style={{ marginTop: 4, fontSize: 12 }}>
              <Text type="secondary">
                毛利率 {periodData?.margin_pct?.toFixed(1) || 0}% · 成本 {formatCurrencyShort(periodData?.cost_amount || 0)}
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 趋势图 */}
      <Card
        size="small"
        title={<Space><CalendarOutlined />每日销售趋势（近{period}天）</Space>}
        style={{ marginBottom: 16 }}
      >
        {trend.length > 0 ? (
          <ReactECharts option={trendOption} style={{ height: 320 }} />
        ) : (
          <Empty description="暂无趋势数据" />
        )}
      </Card>

      {/* Top SKU + 店铺分布 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title={<Space><TrophyOutlined />Top SKU 排行（近{period}天 · 按销售额）</Space>}
          >
            <Table
              dataSource={topSkus}
              columns={topSkuColumns}
              rowKey="spec_no"
              size="small"
              scroll={{ x: 850 }}
              pagination={standardPagination(10)}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            size="small"
            title={<Space><ShopOutlined />店铺销售额分布</Space>}
          >
            {byShop.length > 0 ? (
              <ReactECharts option={shopChartOption} style={{ height: 300 }} />
            ) : (
              <Empty description="暂无店铺数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* 店铺表格 + 仓库表格 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<Space><ShopOutlined />按店铺汇总（近{period}天）</Space>}
          >
            <Table
              dataSource={byShop}
              columns={shopColumns}
              rowKey="shop"
              size="small"
              scroll={{ x: 650 }}
              pagination={standardPagination(10)}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<Space><InboxOutlined />按仓库汇总（近{period}天）</Space>}
          >
            <Table
              dataSource={byWarehouse}
              columns={warehouseColumns}
              rowKey="warehouse"
              size="small"
              scroll={{ x: 600 }}
              pagination={standardPagination(10)}
            />
          </Card>
        </Col>
      </Row>

      {/* 日明细 */}
      <Card
        size="small"
        title={
          <Space>
            <CalendarOutlined />
            单日出库明细
            {dailyDetail?.date && <Tag color="blue">{dailyDetail.date}</Tag>}
            {dailyDetail?.fetch_time && <Text type="secondary" style={{ fontSize: 12 }}>拉取时间: {dailyDetail.fetch_time}</Text>}
          </Space>
        }
        extra={
          overview?.available_dates && overview.available_dates.length > 0 ? (
            <DatePicker
              size="small"
              onChange={(date) => {
                if (date) {
                  const dateStr = date.format('YYYY-MM-DD');
                  loadDailyDetail(dateStr);
                }
              }}
              value={detailDate ? dayjs(detailDate) : null}
              disabledDate={(current) => {
                if (!current) return false;
                const dateStr = current.format('YYYY-MM-DD');
                return !overview.available_dates.includes(dateStr);
              }}
              placeholder="选择日期"
              allowClear={false}
            />
          ) : null
        }
        style={{ marginBottom: 16 }}
      >
        {dailyDetail?.has_data && dailyDetail.details.length > 0 ? (
          <>
            <Row gutter={12} style={{ marginBottom: 12 }}>
              <Col span={4}>
                <Statistic title="出库单" value={dailyDetail.total_orders} suffix="单" valueStyle={{ fontSize: 16 }} />
              </Col>
              <Col span={4}>
                <Statistic title="出库量" value={dailyDetail.total_quantity} suffix="件" valueStyle={{ fontSize: 16 }} />
              </Col>
              <Col span={4}>
                <Statistic title="销售额" value={dailyDetail.total_sell_amount} prefix="¥" precision={0} valueStyle={{ fontSize: 16, color: '#1890ff' }} />
              </Col>
              <Col span={4}>
                <Statistic title="成本" value={dailyDetail.total_cost_amount} prefix="¥" precision={0} valueStyle={{ fontSize: 16, color: '#faad14' }} />
              </Col>
              <Col span={4}>
                <Statistic
                  title="毛利"
                  value={dailyDetail.total_sell_amount - dailyDetail.total_cost_amount}
                  prefix="¥"
                  precision={0}
                  valueStyle={{ fontSize: 16, color: '#52c41a' }}
                />
              </Col>
              <Col span={4}>
                <Statistic title="实收" value={dailyDetail.order_level_receivable} prefix="¥" precision={0} valueStyle={{ fontSize: 16 }} />
              </Col>
            </Row>
            <Table
              dataSource={dailyDetail.details}
              columns={detailColumns}
              rowKey="spec_no"
              size="small"
              scroll={{ x: 1000 }}
              pagination={standardPagination(20)}
            />
          </>
        ) : (
          <Empty description={dailyDetail?.date ? `${dailyDetail.date} 无出库数据` : '请选择日期查看明细'} />
        )}
      </Card>

      {/* 月度汇总 */}
      <Card
        size="small"
        title={<Space><CalendarOutlined />月度汇总</Space>}
      >
        {monthly.length > 0 ? (
          <Table
            dataSource={monthly}
            columns={monthlyColumns}
            rowKey="month"
            size="small"
            scroll={{ x: 900 }}
            pagination={standardPagination(12)}
          />
        ) : (
          <Empty description="暂无月度数据" />
        )}
      </Card>
    </div>
  );
}
