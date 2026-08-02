import { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Table, Tag, DatePicker, Select, Button, Space, Tabs, Segmented } from 'antd';
import ReactECharts from 'echarts-for-react';
import { salesApi } from '../api';
import { usePeriods } from '../hooks/usePeriods';
import type { StoreSales, ProductSales, PlatformSales, CategorySales, StoreOption } from '../types';
import { formatCurrency, formatNumber, formatPercent, formatQty } from '../utils/format';
import dayjs from 'dayjs';

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
    { title: '店铺名称', dataIndex: 'store_name', ellipsis: true },
    { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '订单数', dataIndex: 'order_count', width: 80, render: (v: number) => formatNumber(v) },
    { title: '销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: StoreSales, b: StoreSales) => a.total_revenue - b.total_revenue, defaultSortOrder: 'descend' as const },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v) },
    { title: '折扣', dataIndex: 'total_discount', width: 100, render: (v: number) => formatCurrency(v) },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
    },
  ];

  const productColumns = [
    { title: '排名', width: 60, render: (_: unknown, __: unknown, i: number) => i + 1 },
    { title: 'SKU', dataIndex: 'sku', width: 120 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '分类', dataIndex: 'category', width: 100, render: (v: string | null) => v || '-' },
    { title: '销量', dataIndex: 'total_qty', width: 80, render: (v: number) => formatQty(v), sorter: (a: ProductSales, b: ProductSales) => a.total_qty - b.total_qty },
    { title: '销售额', dataIndex: 'total_revenue', width: 120, render: (v: number) => formatCurrency(v), sorter: (a: ProductSales, b: ProductSales) => a.total_revenue - b.total_revenue, defaultSortOrder: 'descend' as const },
    { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v) },
    { title: '毛利', dataIndex: 'gross_profit', width: 120, render: (v: number) => formatCurrency(v) },
    {
      title: '毛利率',
      dataIndex: 'gross_margin_pct',
      width: 90,
      render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag>,
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
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
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
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
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
                        { title: '店铺数', dataIndex: 'store_count', width: 70 },
                        { title: '订单数', dataIndex: 'order_count', width: 80, render: (v: number) => formatNumber(v) },
                        { title: '销售额', dataIndex: 'total_revenue', width: 110, render: (v: number) => formatCurrency(v) },
                        { title: '毛利率', dataIndex: 'gross_margin_pct', width: 80, render: (v: number) => formatPercent(v) },
                      ]}
                      rowKey="platform"
                      size="small"
                      pagination={false}
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
                        { title: '分类', dataIndex: 'category', width: 120 },
                        { title: 'SKU数', dataIndex: 'sku_count', width: 70 },
                        { title: '销量', dataIndex: 'total_qty', width: 80, render: (v: number) => formatQty(v) },
                        { title: '销售额', dataIndex: 'total_revenue', width: 110, render: (v: number) => formatCurrency(v) },
                        { title: '成本', dataIndex: 'total_cost', width: 100, render: (v: number) => formatCurrency(v) },
                        { title: '毛利', dataIndex: 'gross_profit', width: 110, render: (v: number) => formatCurrency(v) },
                        { title: '毛利率', dataIndex: 'gross_margin_pct', width: 80, render: (v: number) => <Tag color={v >= 70 ? 'green' : v >= 40 ? 'orange' : 'red'}>{formatPercent(v)}</Tag> },
                      ]}
                      rowKey="category"
                      size="small"
                      pagination={false}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </div>
  );
}
