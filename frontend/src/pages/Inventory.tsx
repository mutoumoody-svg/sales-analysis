import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress, Input, Spin, Segmented, Tabs, Tooltip, Select, Space } from 'antd';
import ReactECharts from 'echarts-for-react';
import { inventoryApi } from '../api';
import { usePeriods } from '../hooks/usePeriods';
import type { InventoryHealth, InventoryItem, InventoryAnalysis, InventoryAnalysisItem } from '../types';
import { formatCurrency, formatNumber } from '../utils/format';

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
  const [healthData, setHealthData] = useState<InventoryHealth | null>(null);
  const [analysisData, setAnalysisData] = useState<InventoryAnalysis | null>(null);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

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

  // 概览表列
  const overviewColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-' },
    { title: '仓库', dataIndex: 'warehouse', width: 90, render: (v: string) => <Tag>{v}</Tag> },
    { title: '可售', dataIndex: 'available_qty', width: 70, render: (v: number) => formatNumber(v) },
    { title: '在途', dataIndex: 'inbound_qty', width: 60, render: (v: number) => formatNumber(v) },
    { title: '有效库存', dataIndex: 'effective_qty', width: 80, render: (v: number) => <strong>{formatNumber(v)}</strong> },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      width: 90,
      render: (v: string) => {
        const cfg = riskConfig[v] || riskConfig.healthy;
        return <Tag color={cfg.tagColor}>{cfg.label}</Tag>;
      },
    },
  ];

  // 周转分析列
  const turnoverColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-' },
    { title: '可售库存', dataIndex: 'available_qty', width: 80, render: (v: number) => formatNumber(v) },
    { title: '累计销量', dataIndex: 'total_sold_qty', width: 80, render: (v: number) => formatNumber(v) },
    { title: '日均销量', dataIndex: 'daily_rate', width: 80, render: (v: number) => v > 0 ? v.toFixed(2) : '-' },
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
    },
  ];

  // 滞销分析列
  const staleColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-' },
    { title: '可售库存', dataIndex: 'available_qty', width: 80, render: (v: number) => formatNumber(v) },
    { title: '资金占用', dataIndex: 'capital_occupied', width: 110, render: (v: number) => <span style={{ color: '#ff4d4f' }}>{formatCurrency(v)}</span> },
    { title: '累计销量', dataIndex: 'total_sold_qty', width: 80, render: (v: number) => v > 0 ? formatNumber(v) : <Tag color="red">0</Tag> },
    {
      title: '最后销售',
      dataIndex: 'last_sale_date',
      width: 110,
      render: (v: string | null) => v || <Tag color="red">从未销售</Tag>,
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

  // 补货建议列
  const reorderColumns = [
    { title: 'SKU', dataIndex: 'sku', width: 110 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '品牌', dataIndex: 'brand', width: 90, render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-' },
    { title: '当前库存', dataIndex: 'available_qty', width: 80, render: (v: number) => <span style={{ color: v === 0 ? '#ff4d4f' : '#fa8c16' }}>{formatNumber(v)}</span> },
    { title: '日均销量', dataIndex: 'daily_rate', width: 80, render: (v: number) => v > 0 ? v.toFixed(2) : '-' },
    { title: '安全库存', dataIndex: 'safety_stock', width: 80, render: (v: number) => <strong>{formatNumber(v)}</strong> },
    {
      title: '建议补货量',
      dataIndex: 'reorder_qty',
      width: 100,
      render: (v: number) => v > 0 ? <Tag color="orange">{formatNumber(v)}件</Tag> : <Tag color="green">充足</Tag>,
    },
    {
      title: '紧急程度',
      dataIndex: 'available_qty',
      width: 100,
      render: (v: number) => {
        if (v === 0) return <Tag color="red">紧急</Tag>;
        return <Tag color="orange">建议补货</Tag>;
      },
    },
  ];

  // 过滤数据
  const filteredOverview = (healthData?.items || []).filter((item) => {
    const matchSearch = !search ||
      item.sku.toLowerCase().includes(search.toLowerCase()) ||
      item.product_name.toLowerCase().includes(search.toLowerCase());
    return matchSearch;
  });

  const allAnalysisItems = analysisData?.items || [];
  const filteredAnalysis = allAnalysisItems.filter((item) => {
    const matchSearch = !search ||
      item.sku.toLowerCase().includes(search.toLowerCase()) ||
      item.product_name.toLowerCase().includes(search.toLowerCase());
    return matchSearch;
  });

  const staleItems = allAnalysisItems.filter((i) => i.is_stale);
  const reorderItems = allAnalysisItems.filter((i) => i.needs_reorder).sort((a, b) => b.reorder_qty - a.reorder_qty);

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
        <Input.Search
          placeholder="搜索SKU或商品名"
          allowClear
          style={{ width: 240 }}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

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
                      <Statistic title="分析跨度" value={summary?.date_span || 0} suffix="天" />
                      <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                        {summary?.data_start} ~ {summary?.data_end}
                      </div>
                      <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                        采购周期: 30天
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

                <Card title="库存明细" style={{ marginTop: 16 }}>
                  <Table
                    dataSource={filteredOverview}
                    columns={overviewColumns}
                    rowKey={(r) => `${r.sku}-${r.warehouse}`}
                    size="small"
                    pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
                    scroll={{ x: 700 }}
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
                    pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
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
                      pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
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
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="需补货SKU" value={reorderItems.length} suffix="个" valueStyle={{ color: '#fa8c16' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="紧急缺货" value={reorderItems.filter((i) => i.available_qty === 0).length} suffix="个" valueStyle={{ color: '#ff4d4f' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small"><Statistic title="建议补货总量" value={reorderItems.reduce((s, i) => s + i.reorder_qty, 0)} suffix="件" valueStyle={{ color: '#1677ff' }} /></Card>
                  </Col>
                  <Col xs={12} md={6}>
                    <Card size="small">
                      <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>计算公式</div>
                      <div style={{ fontSize: 13 }}>安全库存 = 日均销量 × 30天</div>
                      <div style={{ fontSize: 13 }}>补货量 = 安全库存 × 2 - 有效库存</div>
                    </Card>
                  </Col>
                </Row>
                <Card title="补货建议明细" style={{ marginTop: 16 }}>
                  {reorderItems.length > 0 ? (
                    <Table
                      dataSource={reorderItems}
                      columns={reorderColumns}
                      rowKey={(r) => `${r.sku}-${r.warehouse}`}
                      size="small"
                      pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
                      scroll={{ x: 700 }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', padding: 40, color: '#52c41a' }}>
                      所有SKU库存充足，暂无补货需求
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
