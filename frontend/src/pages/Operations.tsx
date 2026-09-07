import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, message,
  Modal, Popconfirm, Row, Select, Space, Statistic, Table, Tabs, Tag, Typography,
} from 'antd';
import { CheckOutlined, DeleteOutlined, KeyOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import { operationsApi, salesApi } from '../api';

const { Title, Text } = Typography;

interface QualityIssue { code: string; severity: 'high' | 'medium' | 'low'; count: number; amount?: number }
interface QualityData { period: string; score: number; issues: QualityIssue[] }
interface CostRecord {
  id: string; product_id: string; sku: string; product_name: string; cost_type: string;
  unit_cost: number; effective_date: string; store_id?: string; store_name?: string; channel?: string;
}
interface PurchasePlan {
  id: string; sku: string; product_name: string; suggested_qty: number; confirmed_qty?: number;
  unit_cost?: number; status: string; priority: string; notes?: string; expected_date?: string;
}
interface DailyAlert { id: string; agent_type: string; priority: string; recommendation: string; created_at: string }
interface ProductOption { id: string; sku: string; product_name: string }
interface StoreOption { id: string; store_name: string; channel?: string }
interface IntegrationCheck { key: string; label: string; value?: string; healthy: boolean }
interface IntegrationStatus { overall: 'healthy' | 'attention'; checked_at: string; expected_closed_period: string; checks: IntegrationCheck[] }

const issueNames: Record<string, string> = {
  missing_cost: '缺少成本', missing_brand: '缺少品牌', missing_category: '缺少分类', negative_inventory: '负库存',
};

export default function Operations() {
  const [loading, setLoading] = useState(false);
  const [quality, setQuality] = useState<QualityData | null>(null);
  const [integration, setIntegration] = useState<IntegrationStatus | null>(null);
  const [costs, setCosts] = useState<CostRecord[]>([]);
  const [plans, setPlans] = useState<PurchasePlan[]>([]);
  const [alerts, setAlerts] = useState<DailyAlert[]>([]);
  const [products, setProducts] = useState<ProductOption[]>([]);
  const [stores, setStores] = useState<StoreOption[]>([]);
  const [costOpen, setCostOpen] = useState(false);
  const [confirmPlan, setConfirmPlan] = useState<PurchasePlan | null>(null);
  const [costForm] = Form.useForm();
  const [planForm] = Form.useForm();
  const [adminKey, setAdminKey] = useState(() => sessionStorage.getItem('admin_api_key') || '');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [q, c, p, a, i] = await Promise.all([
        operationsApi.quality(), operationsApi.costs(), operationsApi.purchasePlans(), operationsApi.dailyAlerts(), operationsApi.integrationStatus(),
      ]);
      setQuality(q.data.data); setCosts(c.data.data); setPlans(p.data.data); setAlerts(a.data.data); setIntegration(i.data.data);
    } catch (error) {
      message.error(`运营数据加载失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    load();
    Promise.all([salesApi.products({ limit: 1000 }), salesApi.stores()]).then(([p, s]) => {
      setProducts(p.data.data?.products || p.data.data || []);
      setStores(s.data.data || []);
    });
  }, [load]);

  const saveKey = () => {
    if (adminKey) sessionStorage.setItem('admin_api_key', adminKey); else sessionStorage.removeItem('admin_api_key');
    message.success('管理员密钥仅保存在当前浏览器会话');
  };

  const saveCost = async () => {
    const values = await costForm.validateFields();
    await operationsApi.saveCost({ ...values, effective_date: values.effective_date.format('YYYY-MM-DD') });
    message.success('成本已保存'); setCostOpen(false); costForm.resetFields(); await load();
  };

  const recalculate = async () => {
    const response = await operationsApi.recalculateCosts();
    const data = response.data.data;
    message.success(`已重算 ${data.updated} 条，缺成本 ${data.missing_count} 个 SKU`);
    await load();
  };

  const generatePlans = async () => {
    const response = await operationsApi.generatePurchasePlans();
    message.success(`采购草案已更新，新建 ${response.data.data.created} 条`); await load();
  };

  const submitPlan = async () => {
    if (!confirmPlan) return;
    const values = await planForm.validateFields();
    await operationsApi.updatePurchasePlan(confirmPlan.id, {
      ...values, status: 'confirmed', expected_date: values.expected_date?.format('YYYY-MM-DD'),
    });
    message.success('采购数量已确认'); setConfirmPlan(null); planForm.resetFields(); await load();
  };

  const issueCards = quality?.issues || [];
  const costColumns = useMemo(() => [
    { title: 'SKU', dataIndex: 'sku', width: 140 },
    { title: '商品', dataIndex: 'product_name', ellipsis: true },
    { title: '成本类型', dataIndex: 'cost_type', render: (v: string) => <Tag>{v}</Tag> },
    { title: '范围', render: (_: unknown, r: CostRecord) => r.store_name || r.channel || '全局标准' },
    { title: '单位成本', dataIndex: 'unit_cost', render: (v: number) => `¥${v.toFixed(4)}` },
    { title: '生效日期', dataIndex: 'effective_date' },
    { title: '', width: 56, render: (_: unknown, r: CostRecord) => <Popconfirm title="删除这条成本记录？" onConfirm={async () => { await operationsApi.deleteCost(r.id); await load(); }}><Button danger type="text" icon={<DeleteOutlined />} /></Popconfirm> },
  ], [load]);

  const planColumns = useMemo(() => [
    { title: '优先级', dataIndex: 'priority', render: (v: string) => <Tag color={v === 'urgent' ? 'red' : v === 'normal' ? 'orange' : 'blue'}>{v}</Tag> },
    { title: 'SKU', dataIndex: 'sku' }, { title: '商品', dataIndex: 'product_name', ellipsis: true },
    { title: '建议数量', dataIndex: 'suggested_qty' }, { title: '确认数量', dataIndex: 'confirmed_qty', render: (v?: number) => v ?? '-' },
    { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'confirmed' ? 'green' : 'default'}>{v}</Tag> },
    { title: '操作', render: (_: unknown, r: PurchasePlan) => <Button size="small" icon={<CheckOutlined />} disabled={r.status !== 'draft'} onClick={() => { setConfirmPlan(r); planForm.setFieldsValue({ confirmed_qty: r.suggested_qty, confirmed_by: '管理员' }); }}>确认</Button> },
  ], [planForm]);

  return <div style={{ padding: 24 }}>
    <Title level={3}>运营设置与数据治理</Title>
    <Alert showIcon type="info" message="写操作需要管理员密钥。密钥只保存在当前浏览器会话，不会写入前端代码。" action={<Space><Input.Password prefix={<KeyOutlined />} value={adminKey} onChange={(e) => setAdminKey(e.target.value)} placeholder="X-Admin-Key" /><Button onClick={saveKey}>保存</Button></Space>} />
    <Card style={{ marginTop: 16 }} title="系统对接状态" extra={<Tag color={integration?.overall === 'healthy' ? 'green' : 'red'}>{integration?.overall === 'healthy' ? '全部正常' : '需要处理'}</Tag>}>
      <Row gutter={[12, 12]}>{(integration?.checks || []).map((item) => <Col xs={12} md={8} lg={4} key={item.key}><Card size="small"><Statistic title={item.label} value={item.value || '无数据'} valueStyle={{ fontSize: 18, color: item.healthy ? '#389e0d' : '#cf1322' }} /><Tag color={item.healthy ? 'green' : 'red'}>{item.healthy ? '正常' : '异常/过期'}</Tag></Card></Col>)}</Row>
      <Text type="secondary">上个应结月份：{integration?.expected_closed_period || '-'}；检查时间：{integration?.checked_at ? dayjs(integration.checked_at).format('YYYY-MM-DD HH:mm') : '-'}</Text>
    </Card>
    <Tabs style={{ marginTop: 16 }} items={[
      { key: 'quality', label: '数据质量', children: <>
        <Row gutter={16}><Col span={6}><Card><Statistic title="质量评分" value={quality?.score || 0} suffix="/100" /></Card></Col>{issueCards.map((i) => <Col span={4} key={i.code}><Card><Statistic title={issueNames[i.code] || i.code} value={i.count} valueStyle={{ color: i.severity === 'high' ? '#cf1322' : undefined }} /></Card></Col>)}</Row>
        <Card style={{ marginTop: 16 }} title={`检查期间：${quality?.period || '-'}`} extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={load}>刷新</Button>}>
          <Table rowKey="code" dataSource={issueCards} pagination={false} columns={[{ title: '问题', dataIndex: 'code', render: (v) => issueNames[v] || v }, { title: '严重度', dataIndex: 'severity', render: (v) => <Tag color={v === 'high' ? 'red' : v === 'medium' ? 'orange' : 'blue'}>{v}</Tag> }, { title: '数量', dataIndex: 'count' }, { title: '影响金额', dataIndex: 'amount', render: (v) => v ? `¥${v.toLocaleString()}` : '-' }]} />
        </Card></> },
      { key: 'cost', label: '成本维护', children: <Card extra={<Space><Button type="primary" onClick={() => setCostOpen(true)}>新增成本</Button><Button icon={<SyncOutlined />} onClick={recalculate}>重算当前月份</Button></Space>}><Table rowKey="id" loading={loading} dataSource={costs} columns={costColumns} /></Card> },
      { key: 'purchase', label: '采购清单', children: <Card extra={<Button type="primary" onClick={generatePlans}>生成/更新采购草案</Button>}><Table rowKey="id" loading={loading} dataSource={plans} columns={planColumns} /></Card> },
      { key: 'alerts', label: '日报预警', children: <Card><Table rowKey="id" dataSource={alerts} columns={[{ title: '时间', dataIndex: 'created_at', render: (v) => dayjs(v).format('MM-DD HH:mm') }, { title: 'Agent', dataIndex: 'agent_type' }, { title: '优先级', dataIndex: 'priority', render: (v) => <Tag>{v}</Tag> }, { title: '建议', dataIndex: 'recommendation' }]} /></Card> },
    ]} />

    <Modal title="新增或更新成本" open={costOpen} onCancel={() => setCostOpen(false)} onOk={saveCost} destroyOnHidden>
      <Form form={costForm} layout="vertical" initialValues={{ cost_type: 'standard', effective_date: dayjs() }}>
        <Form.Item name="product_id" label="商品" rules={[{ required: true }]}><Select showSearch optionFilterProp="label" options={products.map((p) => ({ value: p.id, label: `${p.sku} ${p.product_name}` }))} /></Form.Item>
        <Form.Item name="cost_type" label="类型" rules={[{ required: true }]}><Select options={[{ value: 'store', label: '店铺成本' }, { value: 'channel', label: '渠道成本' }, { value: 'standard', label: 'SKU标准成本' }, { value: 'default', label: '默认成本' }]} /></Form.Item>
        <Form.Item noStyle shouldUpdate={(a, b) => a.cost_type !== b.cost_type}>{({ getFieldValue }) => getFieldValue('cost_type') === 'store' ? <Form.Item name="store_id" label="店铺" rules={[{ required: true }]}><Select options={stores.map((s) => ({ value: s.id, label: s.store_name }))} /></Form.Item> : getFieldValue('cost_type') === 'channel' ? <Form.Item name="channel" label="渠道" rules={[{ required: true }]}><Input /></Form.Item> : null}</Form.Item>
        <Row gutter={12}><Col span={12}><Form.Item name="unit_cost" label="单位成本" rules={[{ required: true }]}><InputNumber min={0.0001} precision={4} style={{ width: '100%' }} /></Form.Item></Col><Col span={12}><Form.Item name="effective_date" label="生效日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col></Row>
      </Form>
    </Modal>
    <Modal title={`确认采购：${confirmPlan?.sku || ''}`} open={!!confirmPlan} onCancel={() => setConfirmPlan(null)} onOk={submitPlan}>
      <Form form={planForm} layout="vertical"><Form.Item name="confirmed_qty" label="确认数量" rules={[{ required: true }]}><InputNumber min={0} precision={0} style={{ width: '100%' }} /></Form.Item><Form.Item name="confirmed_by" label="确认人" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="expected_date" label="预计到货"><DatePicker style={{ width: '100%' }} /></Form.Item><Form.Item name="notes" label="备注"><Input.TextArea /></Form.Item></Form>
      <Text type="secondary">建议数量：{confirmPlan?.suggested_qty || 0}</Text>
    </Modal>
  </div>;
}
