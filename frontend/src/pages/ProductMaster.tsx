import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message } from 'antd';
import { EditOutlined, ReloadOutlined } from '@ant-design/icons';
import { operationsApi, salesApi } from '../api';

interface Product { id: string; sku: string; product_name: string; brand?: string; category?: string; unit_cost?: number; status?: string; }

export default function ProductMaster() {
  const [products, setProducts] = useState<Product[]>([]); const [categories, setCategories] = useState<string[]>([]);
  const [keyword, setKeyword] = useState(''); const [missingOnly, setMissingOnly] = useState<string>(); const [editing, setEditing] = useState<Product>(); const [loading, setLoading] = useState(false); const [form] = Form.useForm();
  const load = async () => { setLoading(true); try { const [p,c] = await Promise.all([salesApi.products({limit:1000}), salesApi.categories()]); setProducts(p.data.data || []); setCategories((c.data.data || []).map((x:{category:string})=>x.category).filter(Boolean)); } catch { message.error('商品主数据加载失败'); } finally { setLoading(false); } };
  useEffect(()=>{ load(); },[]);
  const rows = useMemo(()=>products.filter((p)=>{ const q=keyword.toLowerCase(); const hit=!q || `${p.sku} ${p.product_name} ${p.brand||''}`.toLowerCase().includes(q); return hit && (!missingOnly || (missingOnly==='category' ? !p.category : p.unit_cost == null || p.unit_cost <= 0)); }),[products,keyword,missingOnly]);
  const save = async()=>{ if(!editing)return; const values=await form.validateFields(); await operationsApi.updateProduct(editing.id, values); message.success('商品主数据已更新'); setEditing(undefined); await load(); };
  return <div className="page-container"><Typography.Title level={3}>商品主数据</Typography.Title><Alert showIcon type="info" message="Sales、Kucun和Fenxi共用的SKU标准" description="商品分类和标准成本在此维护；更新后销售毛利、赠品成本、库存资金和周转分析使用同一份数据。写入需要先在运营设置保存管理员密钥。" />
    <Card style={{marginTop:16}} extra={<Button icon={<ReloadOutlined/>} onClick={load}>刷新</Button>}><Space wrap style={{marginBottom:16}}><Input.Search allowClear placeholder="搜索SKU、名称或品牌" onSearch={setKeyword} onChange={(e)=>setKeyword(e.target.value)} style={{width:300}}/><Select allowClear placeholder="数据状态" value={missingOnly} onChange={setMissingOnly} style={{width:180}} options={[{value:'category',label:'仅缺分类'},{value:'cost',label:'仅缺成本'}]}/><Tag>共 {rows.length} 个商品</Tag></Space>
      <Table rowKey="id" loading={loading} dataSource={rows} scroll={{x:950}} pagination={{pageSize:50,showSizeChanger:true}} columns={[{title:'SKU',dataIndex:'sku',width:170,fixed:'left'},{title:'商品名称',dataIndex:'product_name',width:330,ellipsis:true},{title:'品牌',dataIndex:'brand',width:140,render:(v)=>v||<Tag color="red">缺失</Tag>},{title:'分类',dataIndex:'category',width:150,render:(v)=>v||<Tag color="red">缺失</Tag>},{title:'标准成本',dataIndex:'unit_cost',width:120,render:(v)=>v!=null&&v>0?`¥${Number(v).toFixed(4)}`:<Tag color="red">缺失</Tag>},{title:'状态',dataIndex:'status',width:90},{title:'操作',fixed:'right',width:80,render:(_:unknown,r:Product)=><Button type="link" icon={<EditOutlined/>} onClick={()=>{setEditing(r);form.setFieldsValue(r);}}>编辑</Button>}]} />
    </Card><Modal title={`编辑商品 · ${editing?.sku||''}`} open={!!editing} onCancel={()=>setEditing(undefined)} onOk={save} destroyOnHidden><Form form={form} layout="vertical"><Form.Item name="product_name" label="商品名称" rules={[{required:true}]}><Input/></Form.Item><Form.Item name="brand" label="品牌"><Input/></Form.Item><Form.Item name="category" label="分类"><Select showSearch allowClear options={categories.map((v)=>({value:v,label:v}))}/></Form.Item><Form.Item name="unit_cost" label="标准单位成本"><InputNumber min={0} precision={4} style={{width:'100%'}}/></Form.Item><Form.Item name="status" label="状态"><Select options={[{value:'active',label:'有效'},{value:'discontinued',label:'停用'}]}/></Form.Item></Form></Modal>
  </div>;
}
