import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Empty, message, Row, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import { CloudSyncOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { monthlyAccountingApi } from '../api';
import { formatCurrency } from '../utils/format';

interface Batch { period: string; status: string; store_count: number; revenue: number; cost: number; gross_profit: number; operating_profit: number; synced_at: string | null; }
interface StoreRow { id: string; store_name: string; platform: string; revenue: number; cost: number; gross_profit: number; ad_fee: number; platform_fee: number; tax_fee: number; logistics_fee: number; operating_profit: number; order_count: number; sales_qty: number; }
interface SummaryData { batch: Batch; operational: { revenue: number; cost: number; profit: number }; difference: { revenue: number; cost: number; profit: number }; stores: StoreRow[]; }

export default function MonthlyAccounting() {
  const [sourcePeriods, setSourcePeriods] = useState<string[]>([]);
  const [synced, setSynced] = useState<Batch[]>([]);
  const [period, setPeriod] = useState<string>();
  const [data, setData] = useState<SummaryData>();
  const [loading, setLoading] = useState(false);

  const loadPeriods = async () => {
    const res = await monthlyAccountingApi.periods();
    const payload = res.data.data;
    setSourcePeriods(payload.source_periods || []);
    setSynced(payload.synced || []);
    const next = period || payload.synced?.[0]?.period || payload.source_periods?.at(-1);
    if (next) setPeriod(next);
  };
  const loadSummary = async (value: string) => {
    try { const res = await monthlyAccountingApi.summary(value); setData(res.data.data); }
    catch { setData(undefined); }
  };
  useEffect(() => { loadPeriods().catch(() => message.error('获取月度数据失败')); }, []);
  useEffect(() => { if (period) loadSummary(period); }, [period]);

  const sync = async () => {
    if (!period) return;
    setLoading(true);
    try {
      await monthlyAccountingApi.sync(period);
      message.success(`${period} 月度核算结果已同步`);
      await loadPeriods(); await loadSummary(period);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      message.error(e.response?.data?.detail || '同步失败，请先在运营设置中填写管理员密钥');
    } finally { setLoading(false); }
  };

  const isSynced = synced.some((item) => item.period === period);
  const columns = [
    { title: '店铺', dataIndex: 'store_name', fixed: 'left' as const, width: 210 },
    { title: '平台', dataIndex: 'platform', width: 80, render: (v: string) => <Tag>{v}</Tag> },
    { title: '销售额', dataIndex: 'revenue', align: 'right' as const, render: formatCurrency },
    { title: '成本', dataIndex: 'cost', align: 'right' as const, render: formatCurrency },
    { title: '毛利', dataIndex: 'gross_profit', align: 'right' as const, render: formatCurrency },
    { title: '广告费', dataIndex: 'ad_fee', align: 'right' as const, render: formatCurrency },
    { title: '平台费', dataIndex: 'platform_fee', align: 'right' as const, render: formatCurrency },
    { title: '税费', dataIndex: 'tax_fee', align: 'right' as const, render: formatCurrency },
    { title: '仓储快递', dataIndex: 'logistics_fee', align: 'right' as const, render: formatCurrency },
    { title: '营销后净利润', dataIndex: 'operating_profit', align: 'right' as const, render: (v: number) => <Typography.Text type={v < 0 ? 'danger' : 'success'}>{formatCurrency(v)}</Typography.Text> },
  ];

  return <div className="page-container">
    <Alert showIcon type="info" icon={<SafetyCertificateOutlined />} message="月度核算口径（公司正式月报）" description="本页直接同步 sales.riverline.com.cn 已完成核算的结果，包含退货扣减、成本、广告、平台费、税费和仓储快递费。原有销售分析保留为实时经营口径。" style={{ marginBottom: 16 }} />
    <Card size="small" style={{ marginBottom: 16 }}><Space wrap>
      <Select value={period} onChange={setPeriod} style={{ width: 170 }} options={sourcePeriods.map((value) => ({ value, label: `${value}${synced.some((b) => b.period === value) ? ' · 已同步' : ' · 待同步'}` }))} />
      <Button type="primary" icon={<CloudSyncOutlined />} loading={loading} onClick={sync}>{isSynced ? '重新同步' : '同步核算结果'}</Button>
      <Typography.Text type="secondary">数据源可用 {sourcePeriods.length} 个月，已同步 {synced.length} 个月</Typography.Text>
    </Space></Card>
    {!data ? <Card><Empty description={isSynced ? '正在加载' : '该月份尚未同步'} /></Card> : <>
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card size="small"><Statistic title="公司月报销售额" value={data.batch.revenue} formatter={(v) => formatCurrency(Number(v))} /></Card></Col>
        <Col xs={12} lg={6}><Card size="small"><Statistic title="总成本" value={data.batch.cost} formatter={(v) => formatCurrency(Number(v))} /></Card></Col>
        <Col xs={12} lg={6}><Card size="small"><Statistic title="毛利" value={data.batch.gross_profit} formatter={(v) => formatCurrency(Number(v))} /></Card></Col>
        <Col xs={12} lg={6}><Card size="small"><Statistic title="营销后净利润" value={data.batch.operating_profit} formatter={(v) => formatCurrency(Number(v))} valueStyle={{ color: data.batch.operating_profit >= 0 ? '#3f8600' : '#cf1322' }} /></Card></Col>
      </Row>
      <Card title="与实时经营口径对账" size="small" style={{ marginTop: 16 }}><Row gutter={[16, 16]}>
        <Col xs={24} md={8}><Statistic title="销售额差异（月报 - 经营）" value={data.difference.revenue} formatter={(v) => formatCurrency(Number(v))} /></Col>
        <Col xs={24} md={8}><Statistic title="成本差异" value={data.difference.cost} formatter={(v) => formatCurrency(Number(v))} /></Col>
        <Col xs={24} md={8}><Statistic title="利润差异" value={data.difference.profit} formatter={(v) => formatCurrency(Number(v))} /></Col>
      </Row></Card>
      <Card title={`店铺核算明细（${data.batch.store_count}家）`} size="small" style={{ marginTop: 16 }}><Table rowKey="id" dataSource={data.stores} columns={columns} scroll={{ x: 1450 }} pagination={false} size="small" /></Card>
    </>}
  </div>;
}
