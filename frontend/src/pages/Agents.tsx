import { useEffect, useState, useCallback } from 'react';
import {
  Row, Col, Card, Table, Spin, Tag, Tabs, Statistic, Progress, List,
  Typography, Space, Alert, Select, Button, Tooltip, Empty, Badge,
} from 'antd';
import {
  RobotOutlined, ThunderboltOutlined, QuestionCircleOutlined,
  BulbOutlined, WarningOutlined, ShoppingOutlined, HddOutlined,
  ShoppingCartOutlined, DollarOutlined, RocketOutlined, ReloadOutlined,
  RiseOutlined, FallOutlined, AlertOutlined,
} from '@ant-design/icons';
import { agentApi, salesApi } from '../api';
import { standardPagination } from '../utils/tableConfig';
import { usePeriods } from '../hooks/usePeriods';
import type {
  AllAgentsResult, CEOAgentResult, SalesAgentResult, InventoryAgentResult,
  ProcurementAgentResult, FinanceAgentResult, OperationAgentResult,
  AgentRecommendation,
} from '../types';
import { formatCurrency, formatCurrencyShort, formatNumber, formatPercent } from '../utils/format';

const { Text, Paragraph, Title } = Typography;

type BrandType = '全部' | '慕咖STTOKE' | '慕咖（MOODY）' | 'MoodyCoffee' | '巴恩天然';

const brandOptions: { label: string; value: BrandType }[] = [
  { label: '全部品牌', value: '全部' },
  { label: '慕咖STTOKE', value: '慕咖STTOKE' },
  { label: '慕咖（MOODY）', value: '慕咖（MOODY）' },
  { label: 'MoodyCoffee', value: 'MoodyCoffee' },
  { label: '巴恩天然', value: '巴恩天然' },
];

const priorityColor: Record<string, string> = {
  High: 'red',
  Medium: 'orange',
  Low: 'green',
};

const priorityIcon: Record<string, React.ReactNode> = {
  High: <AlertOutlined style={{ color: '#ff4d4f' }} />,
  Medium: <WarningOutlined style={{ color: '#faad14' }} />,
  Low: <BulbOutlined style={{ color: '#52c41a' }} />,
};

const statusColor: Record<string, string> = {
  excellent: '#52c41a',
  normal: '#1890ff',
  warning: '#faad14',
  critical: '#ff4d4f',
};

export default function Agents() {
  const [loading, setLoading] = useState(false);
  const [brand, setBrand] = useState<BrandType>('全部');
  const { periods, month, setMonth } = usePeriods();
  const [data, setData] = useState<AllAgentsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (selectedBrand: BrandType, selectedMonth: string) => {
    if (!selectedMonth) return;
    setLoading(true);
    setError(null);
    try {
      const params = selectedBrand === '全部'
        ? { month: selectedMonth }
        : { month: selectedMonth, brand: selectedBrand };
      const resp = await agentApi.runAll(params);
      setData(resp.data?.data || null);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err.response?.data?.detail || err.message || 'Agent分析失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (month) loadData(brand, month);
  }, [month, brand, loadData]);

  const ceo = data?.ceo;
  const sales = data?.agents?.sales;
  const inventory = data?.agents?.inventory;
  const procurement = data?.agents?.procurement;
  const finance = data?.agents?.finance;
  const operation = data?.agents?.operation;

  return (
    <div style={{ padding: 24 }}>
      {/* 顶部控制栏 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Space size="middle">
            <Select
              value={month || undefined}
              onChange={setMonth}
              style={{ width: 160 }}
              placeholder="选择月份"
              options={periods.map((p) => ({
                label: `${p.period} (${formatCurrencyShort(p.net_revenue)})`,
                value: p.period,
              }))}
            />
            <Select
              value={brand}
              onChange={setBrand}
              style={{ width: 160 }}
              options={brandOptions}
            />
          </Space>
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => loadData(brand, month)}
            loading={loading}
          >
            重新分析
          </Button>
        </Col>
      </Row>

      {error && (
        <Alert
          message="分析出错"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Spin spinning={loading} tip="AI Agent 正在分析数据..." size="large">
        {ceo ? (
          <>
            {/* ===== CEO 汇总报告 ===== */}
            <CEOSummary ceo={ceo} />

            {/* ===== 各 Agent 详细分析 ===== */}
            <Card style={{ marginTop: 16 }}>
              <Tabs
                defaultActiveKey="sales"
                items={[
                  {
                    key: 'sales',
                    label: (
                      <span>
                        <ShoppingOutlined /> 销售Agent
                        {sales && countHighPriority(sales.recommendations) > 0 && (
                          <Badge count={countHighPriority(sales.recommendations)} size="small" color="#ff4d4f" offset={[6, -2]} />
                        )}
                      </span>
                    ),
                    children: sales && <SalesAgentView data={sales} />,
                  },
                  {
                    key: 'inventory',
                    label: (
                      <span>
                        <HddOutlined /> 库存Agent
                        {inventory && countHighPriority(inventory.recommendations) > 0 && (
                          <Badge count={countHighPriority(inventory.recommendations)} size="small" color="#ff4d4f" offset={[6, -2]} />
                        )}
                      </span>
                    ),
                    children: inventory && <InventoryAgentView data={inventory} />,
                  },
                  {
                    key: 'procurement',
                    label: (
                      <span>
                        <ShoppingCartOutlined /> 采购Agent
                        {procurement && countHighPriority(procurement.recommendations) > 0 && (
                          <Badge count={countHighPriority(procurement.recommendations)} size="small" color="#ff4d4f" offset={[6, -2]} />
                        )}
                      </span>
                    ),
                    children: procurement && <ProcurementAgentView data={procurement} />,
                  },
                  {
                    key: 'finance',
                    label: (
                      <span>
                        <DollarOutlined /> 财务Agent
                        {finance && countHighPriority(finance.recommendations) > 0 && (
                          <Badge count={countHighPriority(finance.recommendations)} size="small" color="#ff4d4f" offset={[6, -2]} />
                        )}
                      </span>
                    ),
                    children: finance && <FinanceAgentView data={finance} />,
                  },
                  {
                    key: 'operation',
                    label: (
                      <span>
                        <RocketOutlined /> 运营Agent
                        {operation && countHighPriority(operation.recommendations) > 0 && (
                          <Badge count={countHighPriority(operation.recommendations)} size="small" color="#ff4d4f" offset={[6, -2]} />
                        )}
                      </span>
                    ),
                    children: operation && <OperationAgentView data={operation} />,
                  },
                ]}
              />
            </Card>
          </>
        ) : (
          !loading && !error && (
            <Empty
              description="请选择月份后点击运行AI Agent"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )
        )}
      </Spin>
    </div>
  );
}

// ============================================================
// CEO 汇总
// ============================================================
function CEOSummary({ ceo }: { ceo: CEOAgentResult }) {
  const s = ceo.summary;
  const color = statusColor[s.overall_status] || '#1890ff';

  return (
    <div>
      {/* 状态横幅 */}
      <Card
        style={{ marginBottom: 16, borderLeft: `4px solid ${color}` }}
      >
        <Row align="middle" gutter={24}>
          <Col>
            <Space direction="vertical" size={0}>
              <Space>
                <RobotOutlined style={{ fontSize: 28, color }} />
                <Title level={4} style={{ margin: 0 }}>CEO 经营决策报告</Title>
              </Space>
              <Tag color={s.overall_status === 'excellent' ? 'green' : s.overall_status === 'critical' ? 'red' : s.overall_status === 'warning' ? 'orange' : 'blue'} style={{ fontSize: 14, padding: '2px 12px' }}>
                {s.status_text}
              </Tag>
            </Space>
          </Col>
          <Col flex="auto" />
          <Col>
            <Space size="large">
              <Metric label="月销售额" value={formatCurrencyShort(s.revenue)} />
              <Metric label="月利润" value={formatCurrencyShort(s.profit)} />
              <Metric label="毛利率" value={`${s.gross_margin.toFixed(1)}%`} />
              <Metric label="退货率" value={`${s.return_rate.toFixed(1)}%`} />
              <Metric label="发货量" value={formatNumber(s.ship_qty)} />
              <Metric label="库存健康" value={`${s.health_score}/100`} />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 核心指标卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="缺货SKU"
              value={s.stockout_count}
              prefix={s.stockout_count > 0 ? <WarningOutlined style={{ color: '#ff4d4f' }} /> : undefined}
              valueStyle={{ color: s.stockout_count > 0 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="亏损SKU"
              value={s.loss_count}
              prefix={s.loss_count > 0 ? <FallOutlined style={{ color: '#ff4d4f' }} /> : undefined}
              valueStyle={{ color: s.loss_count > 0 ? '#ff4d4f' : undefined }}
            />
            {s.total_loss < 0 && (
              <Text type="danger" style={{ fontSize: 12 }}>合计 {formatCurrencyShort(s.total_loss)}</Text>
            )}
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="滞销SKU"
              value={s.stale_count}
              prefix={s.stale_count > 0 ? <WarningOutlined style={{ color: '#faad14' }} /> : undefined}
              valueStyle={{ color: s.stale_count > 0 ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="紧急补货"
              value={s.urgent_reorder_count}
              suffix={s.urgent_reorder_count > 0 ? ` / ${formatCurrencyShort(s.urgent_reorder_value)}` : ''}
              valueStyle={{ color: s.urgent_reorder_count > 0 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="成本缺失"
              value={s.no_cost_count}
              prefix={s.no_cost_count > 0 ? <WarningOutlined style={{ color: '#faad14' }} /> : undefined}
              valueStyle={{ color: s.no_cost_count > 0 ? '#faad14' : undefined }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={6} lg={4}>
          <Card size="small">
            <Statistic
              title="折扣率"
              value={s.discount_rate.toFixed(1)}
              suffix="%"
              valueStyle={{ color: s.discount_rate > 20 ? '#ff4d4f' : undefined }}
            />
          </Card>
        </Col>
      </Row>

      {s.mom_revenue_change !== undefined && (
        <Row style={{ marginBottom: 16 }}>
          <Col>
            <Alert
              type={s.mom_revenue_change >= 0 ? 'success' : 'warning'}
              showIcon
              icon={s.mom_revenue_change >= 0 ? <RiseOutlined /> : <FallOutlined />}
              message={`销售额环比 ${s.mom_revenue_change >= 0 ? '增长' : '下降'} ${Math.abs(s.mom_revenue_change).toFixed(1)}%`}
              style={{ padding: '4px 16px' }}
            />
          </Col>
        </Row>
      )}

      {/* 三个关键问题 + 三个建议动作 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <QuestionCircleOutlined style={{ color: '#1890ff' }} />
                <span>CEO 需要回答的关键问题</span>
              </Space>
            }
            style={{ height: '100%' }}
          >
            {ceo.questions.length > 0 ? (
              <List
                dataSource={ceo.questions}
                renderItem={(q, idx) => (
                  <List.Item>
                    <Space align="start" style={{ width: '100%' }}>
                      <div
                        style={{
                          minWidth: 28, height: 28, borderRadius: '50%',
                          background: '#1890ff', color: '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 14, fontWeight: 700, flexShrink: 0,
                        }}
                      >
                        {idx + 1}
                      </div>
                      <Text style={{ fontSize: 14, lineHeight: 1.6 }}>{q}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="无关键问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <ThunderboltOutlined style={{ color: '#faad14' }} />
                <span>CEO 建议立即执行的动作</span>
              </Space>
            }
            style={{ height: '100%' }}
          >
            {ceo.actions.length > 0 ? (
              <List
                dataSource={ceo.actions}
                renderItem={(a, idx) => (
                  <List.Item>
                    <Space align="start" style={{ width: '100%' }}>
                      <div
                        style={{
                          minWidth: 28, height: 28, borderRadius: '50%',
                          background: '#faad14', color: '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 14, fontWeight: 700, flexShrink: 0,
                        }}
                      >
                        {idx + 1}
                      </div>
                      <Text style={{ fontSize: 14, lineHeight: 1.6 }}>{a}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="无建议动作" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>
      </Row>

      {/* 高优先级告警 */}
      {ceo.high_priority_alerts.length > 0 && (
        <Card
          title={
            <Space>
              <AlertOutlined style={{ color: '#ff4d4f' }} />
              <span>高优先级告警汇总</span>
              <Tag color="red">{ceo.high_priority_alerts.length} 条</Tag>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <List
            dataSource={ceo.high_priority_alerts}
            renderItem={(item) => (
              <List.Item>
                <Space align="start" style={{ width: '100%' }}>
                  <Tag color="blue" style={{ flexShrink: 0 }}>{agentLabel(item.agent)}</Tag>
                  <Text style={{ fontSize: 13 }}>{item.text}</Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
}

// ============================================================
// 销售Agent
// ============================================================
function SalesAgentView({ data }: { data: SalesAgentResult }) {
  const s = data.summary;
  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="销售额" value={formatCurrencyShort(s.revenue)} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="利润" value={formatCurrencyShort(s.profit)} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="毛利率" value={`${s.gross_margin.toFixed(1)}%`} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="退货率" value={`${s.return_rate.toFixed(1)}%`} valueStyle={{ color: s.return_rate > 10 ? '#ff4d4f' : undefined }} /></Card></Col>
      </Row>

      {data.mom && (
        <Alert
          type={data.mom.revenue_change_pct >= 0 ? 'success' : 'warning'}
          showIcon
          icon={data.mom.revenue_change_pct >= 0 ? <RiseOutlined /> : <FallOutlined />}
          message={`环比${data.mom.prev_period}: 销售额 ${formatCurrencyShort(data.mom.prev_revenue)} → ${formatCurrencyShort(s.revenue)} (${data.mom.revenue_change_pct >= 0 ? '+' : ''}${data.mom.revenue_change_pct.toFixed(1)}%)`}
          style={{ marginBottom: 16 }}
        />
      )}

      {data.sku_concentration !== undefined && (
        <Alert
          type={data.sku_concentration > 60 ? 'warning' : 'info'}
          message={`TOP3 SKU 集中度: ${data.sku_concentration.toFixed(1)}%${data.sku_concentration > 60 ? ' (过高，需分散风险)' : ''}`}
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card title="店铺/渠道表现" size="small" style={{ marginBottom: 16 }}>
            <Table
              size="small"
              dataSource={data.stores}
              rowKey="store_name"
              pagination={standardPagination(10)}
              columns={[
                { title: '店铺', dataIndex: 'store_name', ellipsis: true },
                { title: '平台', dataIndex: 'platform', width: 80 },
                { title: '销售额', dataIndex: 'revenue', width: 100, render: (v: number) => formatCurrencyShort(v), sorter: (a: { revenue: number }, b: { revenue: number }) => a.revenue - b.revenue },
                { title: '利润', dataIndex: 'profit', width: 100, render: (v: number) => formatCurrencyShort(v) },
                { title: '退货率', dataIndex: 'return_rate', width: 80, render: (v: number) => `${v.toFixed(1)}%` },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="TOP 10 畅销SKU" size="small" style={{ marginBottom: 16 }}>
            <Table
              size="small"
              dataSource={data.top_skus}
              rowKey="sku"
              pagination={standardPagination(10)}
              columns={[
                { title: 'SKU', dataIndex: 'sku', width: 80, ellipsis: true },
                { title: '名称', dataIndex: 'name', ellipsis: true },
                { title: '销量', dataIndex: 'qty', width: 70, render: (v: number) => formatNumber(v) },
                { title: '销售额', dataIndex: 'revenue', width: 100, render: (v: number) => formatCurrencyShort(v) },
                { title: '利润', dataIndex: 'profit', width: 100, render: (v: number) => formatCurrencyShort(v) },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {data.high_return_skus.length > 0 && (
        <Card title="高退货SKU (>20%)" size="small" style={{ marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.high_return_skus}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 100 },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '退货率', dataIndex: 'return_rate', width: 100, render: (v: number) => <Text type="danger">{v.toFixed(1)}%</Text> },
              { title: '退货金额', dataIndex: 'return_amount', width: 120, render: (v: number) => formatCurrency(v) },
            ]}
          />
        </Card>
      )}

      <RecommendationList recommendations={data.recommendations} />
    </div>
  );
}

// ============================================================
// 库存Agent
// ============================================================
function InventoryAgentView({ data }: { data: InventoryAgentResult }) {
  const s = data.summary;
  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={s.health_score}
                size={120}
                strokeColor={s.health_score >= 80 ? '#52c41a' : s.health_score >= 60 ? '#faad14' : '#ff4d4f'}
                format={(p) => `${p}`}
              />
              <Text type="secondary">库存健康评分</Text>
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="总SKU" value={s.total_skus} /></Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="健康" value={s.healthy_count} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="缺货" value={s.stockout_count} valueStyle={{ color: s.stockout_count > 0 ? '#ff4d4f' : undefined }} /></Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="低库存" value={s.low_stock_count} valueStyle={{ color: s.low_stock_count > 0 ? '#faad14' : undefined }} /></Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="滞销" value={s.stale_count} valueStyle={{ color: s.stale_count > 0 ? '#faad14' : undefined }} /></Card>
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Card size="small"><Statistic title="资金占用" value={formatCurrencyShort(s.total_capital)} /></Card>
        </Col>
      </Row>

      <Text type="secondary" style={{ fontSize: 12 }}>库存日期: {s.inv_date}</Text>

      {data.stockout_skus.length > 0 && (
        <Card title={<span><Tag color="red">缺货</Tag> 缺货SKU (正在损失销售)</span>} size="small" style={{ marginTop: 16, marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.stockout_skus}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '品牌', dataIndex: 'brand', width: 100 },
              { title: '库存', dataIndex: 'available', width: 70, render: () => <Text type="danger">0</Text> },
              { title: '日均销量', dataIndex: 'daily_rate', width: 90, render: (v: number) => v.toFixed(1) },
              { title: '安全库存', dataIndex: 'safety_stock', width: 80 },
              { title: '资金占用', dataIndex: 'capital', width: 100, render: (v: number) => formatCurrencyShort(v) },
            ]}
          />
        </Card>
      )}

      {data.stale_skus.length > 0 && (
        <Card title={<span><Tag color="orange">滞销</Tag> 滞销SKU (资金被无效占用)</span>} size="small" style={{ marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.stale_skus}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '库存', dataIndex: 'available', width: 70 },
              { title: '月销量', dataIndex: 'sold_qty', width: 70, render: (v: number) => <Text type="warning">{v}</Text> },
              { title: '资金占用', dataIndex: 'capital', width: 100, render: (v: number) => formatCurrencyShort(v) },
            ]}
          />
        </Card>
      )}

      <RecommendationList recommendations={data.recommendations} />
    </div>
  );
}

// ============================================================
// 采购Agent
// ============================================================
function ProcurementAgentView({ data }: { data: ProcurementAgentResult }) {
  const s = data.summary;
  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="紧急补货" value={s.urgent_count} valueStyle={{ color: s.urgent_count > 0 ? '#ff4d4f' : undefined }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="常规补货" value={s.normal_count} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="紧急采购金额" value={formatCurrencyShort(s.urgent_value)} valueStyle={{ color: s.urgent_value > 0 ? '#ff4d4f' : undefined }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="采购总预算" value={formatCurrencyShort(s.total_reorder_value)} /></Card></Col>
      </Row>

      {data.urgent_reorders.length > 0 && (
        <Card
          title={<span><Tag color="red">紧急</Tag> 紧急补货清单 (7天内将缺货)</span>}
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Table
            size="small"
            dataSource={data.urgent_reorders}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '当前库存', dataIndex: 'available', width: 80, render: (v: number) => <Text type="danger">{v}</Text> },
              { title: '日均销量', dataIndex: 'daily_rate', width: 90, render: (v: number) => v.toFixed(1) },
              { title: '安全库存', dataIndex: 'safety_stock', width: 80 },
              { title: '建议采购量', dataIndex: 'reorder_qty', width: 100, render: (v: number) => <Text strong>{formatNumber(v)} 件</Text> },
              { title: '单价', dataIndex: 'unit_cost', width: 80, render: (v: number) => formatCurrencyShort(v) },
              { title: '采购金额', dataIndex: 'reorder_value', width: 110, render: (v: number) => formatCurrency(v) },
              { title: '可供天数', dataIndex: 'days_of_supply', width: 80, render: (v: number) => <Text type={v < 3 ? 'danger' : 'warning'}>{v}天</Text> },
            ]}
          />
        </Card>
      )}

      {data.normal_reorders.length > 0 && (
        <Card
          title={<span><Tag color="orange">常规</Tag> 常规补货清单 (30天内需补货)</span>}
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Table
            size="small"
            dataSource={data.normal_reorders}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '当前库存', dataIndex: 'available', width: 80 },
              { title: '日均销量', dataIndex: 'daily_rate', width: 90, render: (v: number) => v.toFixed(1) },
              { title: '建议采购量', dataIndex: 'reorder_qty', width: 100, render: (v: number) => <Text strong>{formatNumber(v)} 件</Text> },
              { title: '采购金额', dataIndex: 'reorder_value', width: 110, render: (v: number) => formatCurrency(v) },
              { title: '可供天数', dataIndex: 'days_of_supply', width: 80, render: (v: number) => `${v}天` },
            ]}
          />
        </Card>
      )}

      <RecommendationList recommendations={data.recommendations} />
    </div>
  );
}

// ============================================================
// 财务Agent
// ============================================================
function FinanceAgentView({ data }: { data: FinanceAgentResult }) {
  const s = data.summary;
  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="销售额" value={formatCurrencyShort(s.revenue)} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="成本" value={formatCurrencyShort(s.cost)} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="利润" value={formatCurrencyShort(s.profit)} valueStyle={{ color: s.profit >= 0 ? '#52c41a' : '#ff4d4f' }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="毛利率" value={`${s.gross_margin.toFixed(1)}%`} valueStyle={{ color: s.gross_margin < 20 ? '#ff4d4f' : s.gross_margin >= 40 ? '#52c41a' : undefined }} /></Card></Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8}><Card size="small"><Statistic title="成本占比" value={`${s.cost_ratio.toFixed(1)}%`} /></Card></Col>
        <Col xs={12} sm={8}><Card size="small"><Statistic title="佣金占比" value={`${s.commission_ratio.toFixed(1)}%`} valueStyle={{ color: s.commission_ratio > 15 ? '#faad14' : undefined }} /></Card></Col>
        <Col xs={12} sm={8}><Card size="small"><Statistic title="发货毛利" value={`${s.ship_margin.toFixed(1)}%`} /></Card></Col>
      </Row>

      {data.by_brand.length > 0 && (
        <Card title="品牌利润对比" size="small" style={{ marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.by_brand}
            rowKey="brand"
            pagination={standardPagination(10)}
            columns={[
              { title: '品牌', dataIndex: 'brand', width: 120 },
              { title: '销售额', dataIndex: 'revenue', width: 120, render: (v: number) => formatCurrencyShort(v), sorter: (a: { revenue: number }, b: { revenue: number }) => a.revenue - b.revenue },
              { title: '成本', dataIndex: 'cost', width: 120, render: (v: number) => formatCurrencyShort(v) },
              { title: '利润', dataIndex: 'profit', width: 120, render: (v: number) => <Text style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{formatCurrencyShort(v)}</Text> },
              { title: '毛利率', dataIndex: 'margin', width: 100, render: (v: number) => <Tag color={v >= 40 ? 'green' : v >= 20 ? 'orange' : 'red'}>{v.toFixed(1)}%</Tag> },
            ]}
          />
        </Card>
      )}

      {data.loss_skus.length > 0 && (
        <Card
          title={<span><Tag color="red">亏损</Tag> 亏损SKU (合计 {formatCurrencyShort(data.total_loss)})</span>}
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Table
            size="small"
            dataSource={data.loss_skus}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '销量', dataIndex: 'qty', width: 70 },
              { title: '销售额', dataIndex: 'revenue', width: 100, render: (v: number) => formatCurrencyShort(v) },
              { title: '成本', dataIndex: 'cost', width: 100, render: (v: number) => formatCurrencyShort(v) },
              { title: '亏损', dataIndex: 'profit', width: 100, render: (v: number) => <Text type="danger">{formatCurrency(v)}</Text> },
            ]}
          />
        </Card>
      )}

      {data.no_cost_sku_count > 0 && (
        <Alert
          type="error"
          showIcon
          message={`${data.no_cost_sku_count} 个SKU缺少成本数据，涉及销售额 ${formatCurrencyShort(data.no_cost_revenue)}，利润计算不准确！`}
          style={{ marginBottom: 16 }}
        />
      )}

      <RecommendationList recommendations={data.recommendations} />
    </div>
  );
}

// ============================================================
// 运营Agent
// ============================================================
function OperationAgentView({ data }: { data: OperationAgentResult }) {
  const s = data.summary;
  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="发货金额" value={formatCurrencyShort(s.ship_amount)} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="净销售额" value={formatCurrencyShort(s.net_amount)} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="折扣率" value={`${s.discount_rate.toFixed(1)}%`} valueStyle={{ color: s.discount_rate > 20 ? '#ff4d4f' : undefined }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="客单价" value={formatCurrency(s.avg_order_value)} /></Card></Col>
      </Row>

      {s.discount_amount > 0 && (
        <Alert
          type={s.discount_rate > 20 ? 'warning' : 'info'}
          message={`折扣总额: ${formatCurrency(s.discount_amount)} (折扣率 ${s.discount_rate.toFixed(1)}%)`}
          style={{ marginBottom: 16 }}
        />
      )}

      {data.low_margin_skus.length > 0 && (
        <Card title={<span><Tag color="orange">低毛利</Tag> 低毛利SKU及定价建议 (毛利率 &lt;30%)</span>} size="small" style={{ marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.low_margin_skus}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '销量', dataIndex: 'qty', width: 70 },
              { title: '销售额', dataIndex: 'revenue', width: 100, render: (v: number) => formatCurrencyShort(v) },
              { title: '成本', dataIndex: 'cost', width: 100, render: (v: number) => formatCurrencyShort(v) },
              { title: '利润', dataIndex: 'profit', width: 90, render: (v: number) => formatCurrencyShort(v) },
              { title: '当前毛利率', dataIndex: 'margin', width: 100, render: (v: number) => <Tag color={v < 0 ? 'red' : 'orange'}>{v.toFixed(1)}%</Tag> },
              { title: '建议单价', dataIndex: 'suggested_price', width: 100, render: (v: number) => <Text type="success">{formatCurrency(v)}</Text> },
            ]}
          />
        </Card>
      )}

      {data.promo_opportunities.length > 0 && (
        <Card title={<span><Tag color="blue">促销</Tag> 促销机会 (滞销库存清仓)</span>} size="small" style={{ marginBottom: 16 }}>
          <Table
            size="small"
            dataSource={data.promo_opportunities}
            rowKey="sku"
            pagination={standardPagination(10)}
            columns={[
              { title: 'SKU', dataIndex: 'sku', width: 90, ellipsis: true },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '库存', dataIndex: 'available', width: 70 },
              { title: '月销量', dataIndex: 'monthly_sales', width: 80, render: (v: number) => <Text type="warning">{v}</Text> },
              { title: '资金占用', dataIndex: 'capital', width: 100, render: (v: number) => formatCurrencyShort(v) },
              { title: '建议动作', dataIndex: 'suggested_action', width: 150, render: (v: string) => <Tag color="blue">{v}</Tag> },
            ]}
          />
        </Card>
      )}

      <RecommendationList recommendations={data.recommendations} />
    </div>
  );
}

// ============================================================
// 通用组件
// ============================================================
function RecommendationList({ recommendations }: { recommendations: AgentRecommendation[] }) {
  if (!recommendations || recommendations.length === 0) return null;
  return (
    <Card title="AI 建议与洞察" size="small">
      <List
        dataSource={recommendations}
        renderItem={(rec) => (
          <List.Item>
            <Space align="start" style={{ width: '100%' }}>
              {priorityIcon[rec.priority] || <BulbOutlined />}
              <Text style={{ flex: 1, fontSize: 13, lineHeight: 1.6 }}>{rec.recommendation}</Text>
              <Tag color={priorityColor[rec.priority]}>{rec.priority}</Tag>
            </Space>
          </List.Item>
        )}
      />
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>{label}</Text>
      <Text strong style={{ fontSize: 18 }}>{value}</Text>
    </div>
  );
}

// ============================================================
// 工具函数
// ============================================================
function countHighPriority(recs: AgentRecommendation[]): number {
  return recs.filter((r) => r.priority === 'High').length;
}

function agentLabel(key: string): string {
  const labels: Record<string, string> = {
    sales: '销售',
    inventory: '库存',
    procurement: '采购',
    finance: '财务',
    operation: '运营',
  };
  return labels[key] || key;
}
