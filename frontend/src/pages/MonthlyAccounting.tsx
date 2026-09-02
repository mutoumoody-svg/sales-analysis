import { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Empty, Form, InputNumber, message, Modal, Row, Select, Space, Statistic, Table, Tag, Typography, Upload } from 'antd';
import { CloudSyncOutlined, DownloadOutlined, EditOutlined, InboxOutlined, SafetyCertificateOutlined, UploadOutlined } from '@ant-design/icons';
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
  const [detailFile, setDetailFile] = useState<File>();
  const [summaryFile, setSummaryFile] = useState<File>();
  const [editing, setEditing] = useState<StoreRow>();
  const [feeForm] = Form.useForm();

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

  const importMonth = async () => {
    if (!period || !detailFile || !summaryFile) { message.warning('请选择月份并上传两个文件'); return; }
    setLoading(true);
    try {
      await monthlyAccountingApi.importMonth(period, detailFile, summaryFile);
      message.success('核算完成，请检查店铺费用后确认月报');
      setDetailFile(undefined); setSummaryFile(undefined); await loadPeriods(); await loadSummary(period);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      message.error(e.response?.data?.detail || '文件核算失败');
    } finally { setLoading(false); }
  };

  const saveFees = async () => {
    if (!editing) return;
    const values = await feeForm.validateFields();
    await monthlyAccountingApi.updateFees(editing.id, values);
    message.success('费用已更新'); setEditing(undefined); if (period) await loadSummary(period);
  };

  const confirmMonth = async () => {
    if (!period) return;
    await monthlyAccountingApi.confirm(period); message.success(`${period} 已确认为正式月报`); await loadPeriods(); await loadSummary(period);
  };

  const exportMonth = async () => {
    if (!period) return;
    const res = await monthlyAccountingApi.export(period);
    const url = URL.createObjectURL(res.data); const link = document.createElement('a'); link.href = url; link.download = `monthly-accounting-${period}.xlsx`; link.click(); URL.revokeObjectURL(url);
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
    { title: '操作', fixed: 'right' as const, width: 80, render: (_: unknown, row: StoreRow) => <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(row); feeForm.setFieldsValue(row); }}>费用</Button> },
  ];

  return <div className="page-container">
    <Alert showIcon type="info" icon={<SafetyCertificateOutlined />} message="月度核算口径（公司正式月报）" description="本页直接同步 sales.riverline.com.cn 已完成核算的结果，包含退货扣减、成本、广告、平台费、税费和仓储快递费。原有销售分析保留为实时经营口径。" style={{ marginBottom: 16 }} />
    <Card title="统一月度数据导入" size="small" style={{ marginBottom: 16 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}><Upload.Dragger accept=".xlsx,.xls" maxCount={1} beforeUpload={(file) => { setDetailFile(file); return false; }} onRemove={() => { setDetailFile(undefined); }} fileList={detailFile ? [detailFile as never] : []}><p><InboxOutlined /></p><b>销售出库明细</b><p>主销售数据（约94列）</p></Upload.Dragger></Col>
        <Col xs={24} md={12}><Upload.Dragger accept=".xlsx,.xls" maxCount={1} beforeUpload={(file) => { setSummaryFile(file); return false; }} onRemove={() => { setSummaryFile(undefined); }} fileList={summaryFile ? [summaryFile as never] : []}><p><InboxOutlined /></p><b>货品销售汇总</b><p>用于退货金额和数量扣减（约23列）</p></Upload.Dragger></Col>
      </Row>
      <Button type="primary" icon={<UploadOutlined />} loading={loading} onClick={importMonth} style={{ marginTop: 16 }}>上传并核算</Button>
    </Card>
    <Card size="small" style={{ marginBottom: 16 }}><Space wrap>
      <Select value={period} onChange={setPeriod} style={{ width: 170 }} options={sourcePeriods.map((value) => ({ value, label: `${value}${synced.some((b) => b.period === value) ? ' · 已同步' : ' · 待同步'}` }))} />
      <Button icon={<CloudSyncOutlined />} loading={loading} onClick={sync}>{isSynced ? '从旧系统重新同步' : '从旧系统同步'}</Button>
      {data && <Button type="primary" onClick={confirmMonth} disabled={data.batch.status === 'confirmed'}>{data.batch.status === 'confirmed' ? '已确认' : '确认月报'}</Button>}
      {data && <Button icon={<DownloadOutlined />} onClick={exportMonth}>导出 Excel</Button>}
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
    <Modal title={`${editing?.store_name || ''} · 费用录入`} open={!!editing} onCancel={() => setEditing(undefined)} onOk={saveFees} destroyOnHidden>
      <Alert type="warning" showIcon message="税费单独展示；营销后净利润 = 毛利 - 广告费 - 平台费 - 仓储快递费。" style={{ marginBottom: 16 }} />
      <Form form={feeForm} layout="vertical">
        <Form.Item name="ad_fee" label="广告费" initialValue={0}><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
        <Form.Item name="platform_fee" label="平台费/佣金" initialValue={0}><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
        <Form.Item name="tax_fee" label="税费" initialValue={0}><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
        <Form.Item name="logistics_fee" label="仓储快递费" initialValue={0}><InputNumber min={0} precision={2} style={{ width: '100%' }} /></Form.Item>
      </Form>
    </Modal>
  </div>;
}
