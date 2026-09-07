import { useEffect, useMemo, useState } from 'react';
import { Card, Col, Empty, Row, Select, Statistic, Table, Tag, Typography, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import { monthlyAccountingApi } from '../api';
import { formatCurrency } from '../utils/format';

interface MonthRow { period: string; status: string; store_count: number; revenue: number; cost: number; gross_profit: number; operating_profit: number; }
interface StoreRow { period: string; store_name: string; platform: string; revenue: number; cost: number; gross_profit: number; operating_profit: number; order_count: number; sales_qty: number; }

export default function AnnualSales() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [months, setMonths] = useState<MonthRow[]>([]);
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    monthlyAccountingApi.yearDetail(year).then((res) => {
      setMonths(res.data.data.months || []); setStores(res.data.data.stores || []);
    }).catch(() => message.error('年度销售数据加载失败')).finally(() => setLoading(false));
  }, [year]);

  const totals = useMemo(() => months.reduce((a, r) => ({
    revenue: a.revenue + r.revenue, cost: a.cost + r.cost,
    gross: a.gross + r.gross_profit, operating: a.operating + r.operating_profit,
  }), { revenue: 0, cost: 0, gross: 0, operating: 0 }), [months]);

  const storeSummary = useMemo(() => {
    const map = new Map<string, StoreRow>();
    stores.forEach((r) => {
      const key = `${r.platform}|${r.store_name}`; const old = map.get(key);
      map.set(key, old ? { ...old, revenue: old.revenue + r.revenue, cost: old.cost + r.cost, gross_profit: old.gross_profit + r.gross_profit, operating_profit: old.operating_profit + r.operating_profit, order_count: old.order_count + r.order_count, sales_qty: old.sales_qty + r.sales_qty } : { ...r });
    });
    return [...map.values()].sort((a, b) => b.revenue - a.revenue);
  }, [stores]);

  const chart = { tooltip: { trigger: 'axis' }, legend: { data: ['销售额', '毛利', '营销后净利润'] }, grid: { left: 70, right: 24, top: 50, bottom: 40 }, xAxis: { type: 'category', data: months.map((m) => m.period) }, yAxis: { type: 'value' }, series: [
    { name: '销售额', type: 'bar', data: months.map((m) => m.revenue) },
    { name: '毛利', type: 'line', data: months.map((m) => m.gross_profit) },
    { name: '营销后净利润', type: 'line', data: months.map((m) => m.operating_profit) },
  ] };

  return <div className="page-container">
    <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}><Typography.Title level={3} style={{ margin: 0 }}>年度销售分析</Typography.Title><Select value={year} onChange={setYear} style={{ width: 120 }} options={[0,1,2].map((n) => ({ value: currentYear - n, label: `${currentYear - n}年` }))} /></Row>
    <Row gutter={[16,16]}><Col xs={12} lg={6}><Card><Statistic title="年度销售额" value={totals.revenue} formatter={(v) => formatCurrency(Number(v))} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="年度成本" value={totals.cost} formatter={(v) => formatCurrency(Number(v))} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="年度毛利" value={totals.gross} formatter={(v) => formatCurrency(Number(v))} /></Card></Col><Col xs={12} lg={6}><Card><Statistic title="营销后净利润" value={totals.operating} formatter={(v) => formatCurrency(Number(v))} valueStyle={{ color: totals.operating >= 0 ? '#389e0d' : '#cf1322' }} /></Card></Col></Row>
    {!months.length && !loading ? <Card style={{ marginTop: 16 }}><Empty description="该年度暂无已核算月报" /></Card> : <>
      <Card title="月度趋势" style={{ marginTop: 16 }}><ReactECharts option={chart} style={{ height: 360 }} /></Card>
      <Card title="月度正式核算" style={{ marginTop: 16 }}><Table rowKey="period" loading={loading} dataSource={months} pagination={false} columns={[{ title:'月份', dataIndex:'period' }, { title:'状态', dataIndex:'status', render:(v)=><Tag color={v==='confirmed'?'green':'orange'}>{v==='confirmed'?'已确认':'待确认'}</Tag> }, { title:'店铺', dataIndex:'store_count' }, { title:'销售额', dataIndex:'revenue', render:formatCurrency }, { title:'成本', dataIndex:'cost', render:formatCurrency }, { title:'毛利', dataIndex:'gross_profit', render:formatCurrency }, { title:'营销后净利润', dataIndex:'operating_profit', render:formatCurrency }]} /></Card>
      <Card title="年度店铺汇总" style={{ marginTop: 16 }}><Table rowKey={(r)=>`${r.platform}-${r.store_name}`} dataSource={storeSummary} scroll={{x:900}} columns={[{ title:'平台', dataIndex:'platform' }, { title:'店铺', dataIndex:'store_name' }, { title:'销售额', dataIndex:'revenue', render:formatCurrency }, { title:'成本', dataIndex:'cost', render:formatCurrency }, { title:'毛利', dataIndex:'gross_profit', render:formatCurrency }, { title:'营销后净利润', dataIndex:'operating_profit', render:formatCurrency }, { title:'订单数', dataIndex:'order_count' }, { title:'销量', dataIndex:'sales_qty' }]} /></Card>
    </>}
  </div>;
}
