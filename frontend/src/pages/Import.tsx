import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Upload, message, Alert, Table, Spin, DatePicker, Space, Typography } from 'antd';
import { InboxOutlined, DatabaseOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import dayjs from 'dayjs';
import { importApi } from '../api';

const { Dragger } = Upload;

interface ImportStatus {
  table_counts: Record<string, number>;
  total_records: number;
}

export default function ImportPage() {
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [summaryPeriod, setSummaryPeriod] = useState<dayjs.Dayjs | null>(null);
  const [detailPeriod, setDetailPeriod] = useState<dayjs.Dayjs | null>(null);

  const loadStatus = () => {
    setLoading(true);
    importApi
      .status()
      .then((res) => setStatus(res.data.data))
      .catch(() => message.error('获取数据库状态失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const createUploadProps = (type: 'detail' | 'summary' | 'inventory'): UploadProps => ({
    name: 'file',
    multiple: false,
    accept: '.xlsx,.xls',
    showUploadList: false,
    customRequest: async (options) => {
      const { file } = options;
      setUploading(type);
      try {
        const labels = { detail: '销售明细', summary: '货品汇总', inventory: '库存' };
        const periodStr = type === 'summary' && summaryPeriod
          ? summaryPeriod.format('YYYY-MM')
          : type === 'detail' && detailPeriod
          ? detailPeriod.format('YYYY-MM')
          : undefined;
        let res;
        if (type === 'detail') {
          res = await importApi.uploadDetail(file as File, periodStr);
        } else if (type === 'summary') {
          res = await importApi.uploadSummary(file as File, periodStr);
        } else {
          res = await importApi.uploadInventory(file as File);
        }
        const d = res.data;
        if (d.status === 'success' || d.status === 'partial') {
          const data = d.data || {};
          const count = data.processed || 0;
          const msg = d.status === 'partial' && data.error_count > 0
            ? `${labels[type]}导入完成（${count} 条），但有 ${data.error_count} 个错误`
            : `${labels[type]}导入成功：${count} 条`;
          message.success(msg);
          loadStatus();
        } else {
          message.error(`${labels[type]}导入失败：${d.message || d.detail || '未知错误'}`);
        }
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } }; message?: string };
        message.error(`导入失败：${e.response?.data?.detail || e.message || '网络错误'}`);
      } finally {
        setUploading(null);
      }
    },
  });

  const draggerStyle = { height: 200 };

  const dbColumns = [
    { title: '数据表', dataIndex: 'table', width: 150 },
    { title: '记录数', dataIndex: 'count', width: 120, render: (v: number) => (v || 0).toLocaleString('zh-CN') },
  ];

  const tc = status?.table_counts || {};
  const dbData = status
    ? [
        { table: '店铺', count: tc.stores || 0 },
        { table: '商品', count: tc.products || 0 },
        { table: '客户', count: tc.customers || 0 },
        { table: '订单', count: tc.orders || 0 },
        { table: '订单明细', count: tc.order_items || 0 },
        { table: '货品销售汇总', count: tc.sales_summary || 0 },
        { table: '库存', count: tc.inventory || 0 },
        { table: '费用', count: tc.expenses || 0 },
        { table: '利润分析', count: tc.profit_analysis || 0 },
      ]
    : [];

  return (
    <div className="page-container">
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="销售出库明细" size="small">
            <Space direction="vertical" style={{ width: '100%', marginBottom: 8 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                选择数据所属月份（不选则自动从"下单时间"列识别日期）
              </Typography.Text>
              <DatePicker
                picker="month"
                value={detailPeriod}
                onChange={(v) => setDetailPeriod(v)}
                format="YYYY-MM"
                style={{ width: '100%' }}
                placeholder="例如：2026-06"
              />
            </Space>
            <Dragger {...createUploadProps('detail')} style={draggerStyle} disabled={uploading !== null}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">{uploading === 'detail' ? '导入中...' : '点击或拖拽文件'}</p>
              <p className="ant-upload-hint">旺店通「销售出库明细表」.xlsx</p>
            </Dragger>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="货品销售汇总" size="small">
            <Space direction="vertical" style={{ width: '100%', marginBottom: 8 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                选择数据所属月份（不选则从文件名自动推断）
              </Typography.Text>
              <DatePicker
                picker="month"
                value={summaryPeriod}
                onChange={(v) => setSummaryPeriod(v)}
                format="YYYY-MM"
                style={{ width: '100%' }}
                placeholder="例如：2026-06"
              />
            </Space>
            <Dragger {...createUploadProps('summary')} style={draggerStyle} disabled={uploading !== null}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">{uploading === 'summary' ? '导入中...' : '点击或拖拽文件'}</p>
              <p className="ant-upload-hint">旺店通「货品销售汇总表」.xlsx</p>
            </Dragger>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="库存数据" size="small">
            <Dragger {...createUploadProps('inventory')} style={draggerStyle} disabled={uploading !== null}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">{uploading === 'inventory' ? '导入中...' : '点击或拖拽文件'}</p>
              <p className="ant-upload-hint">库存整理 .xlsx</p>
            </Dragger>
          </Card>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        message="导入说明"
        description={'三个文件可独立上传。明细表和汇总表均支持月份选择器（不选则自动识别）。明细表自动从"下单时间"列识别日期，汇总表从文件名推断月份。导入会自动识别平台、过滤合计行、匹配成本数据。'}
        style={{ marginTop: 16 }}
      />

      <Card
        title="数据库状态"
        style={{ marginTop: 16 }}
        extra={<DatabaseOutlined />}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col xs={12} md={4}>
                <Statistic title="店铺" value={tc.stores || 0} />
              </Col>
              <Col xs={12} md={4}>
                <Statistic title="商品" value={tc.products || 0} />
              </Col>
              <Col xs={12} md={4}>
                <Statistic title="订单" value={tc.orders || 0} />
              </Col>
              <Col xs={12} md={4}>
                <Statistic title="订单明细" value={tc.order_items || 0} />
              </Col>
              <Col xs={12} md={4}>
                <Statistic title="销售汇总" value={tc.sales_summary || 0} />
              </Col>
              <Col xs={12} md={4}>
                <Statistic title="库存" value={tc.inventory || 0} />
              </Col>
            </Row>
            <Table
              dataSource={dbData}
              columns={dbColumns}
              rowKey="table"
              size="small"
              pagination={false}
            />
          </>
        )}
      </Card>
    </div>
  );
}
