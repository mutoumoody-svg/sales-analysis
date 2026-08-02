"""交叉验证：销售出库明细表 vs 货品销售汇总表 v2"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

f_detail = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx'
f_summary = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx'

df_d = pd.read_excel(f_detail, sheet_name='Sheet1')
df_s = pd.read_excel(f_summary, sheet_name='Sheet1')

print('=' * 80)
print('1. 订单号分析（明细表）')
print('=' * 80)
print(f'总行数: {len(df_d)}')
print(f'唯一订单号数: {df_d["订单编号"].nunique()}')
print(f'空订单号数: {df_d["订单编号"].isna().sum()}')

print(f'\n订单类型分布:')
print(df_d['订单类型'].value_counts().to_string())

order_counts = df_d.groupby('订单编号').size()
print(f'\n每单明细行数分布:')
print(f'  1行/单: {(order_counts == 1).sum()} 个订单')
print(f'  2行/单: {(order_counts == 2).sum()} 个订单')
print(f'  3行/单: {(order_counts == 3).sum()} 个订单')
print(f'  4行/单: {(order_counts == 4).sum()} 个订单')
print(f'  5+行/单: {(order_counts >= 5).sum()} 个订单')
print(f'  最多: {order_counts.max()}行 (订单号: {order_counts.idxmax()})')

print('\n' + '=' * 80)
print('2. 明细表按 店铺×货品编号 汇总')
print('=' * 80)

# 明细表按 店铺+商家编码 汇总
detail_agg = df_d.groupby(['店铺', '商家编码']).agg(
    明细_发货数量=('货品数量', 'sum'),
    明细_发货金额=('货品成交总价', 'sum'),
    明细_货品总成本=('货品总成本', 'sum'),
    明细_货品名称=('货品名称', 'first'),
    明细_行数=('货品数量', 'count'),
).reset_index()
detail_agg.rename(columns={'商家编码': '货品编号'}, inplace=True)
print(f'明细表 店铺×货品 组合数: {len(detail_agg)}')

# 汇总表
summary_agg = df_s[['店铺', '货品编号', '货品名称', '发货总量', '退货总量', '实际销售量',
                     '发货总金额', '退货总金额', '实际销售额', '货品总成本', '退货总成本',
                     '实际总成本', '实际总利润']].copy()
summary_agg.rename(columns={
    '货品名称': '汇总_货品名称',
    '发货总量': '汇总_发货数量',
    '退货总量': '汇总_退货数量',
    '实际销售量': '汇总_实际销售量',
    '发货总金额': '汇总_发货金额',
    '退货总金额': '汇总_退货金额',
    '实际销售额': '汇总_实际销售额',
    '货品总成本': '汇总_货品总成本',
    '退货总成本': '汇总_退货总成本',
    '实际总成本': '汇总_实际总成本',
    '实际总利润': '汇总_实际总利润',
}, inplace=True)
print(f'汇总表 店铺×货品 组合数: {len(summary_agg)}')

print('\n' + '=' * 80)
print('3. 金额总量对比')
print('=' * 80)

print('--- 明细表 ---')
print(f'  货品数量合计: {df_d["货品数量"].sum():,}')
print(f'  货品成交总价合计: {df_d["货品成交总价"].sum():,.2f}')
print(f'  货品总成本合计: {df_d["货品总成本"].sum():,.2f}')
print(f'  订单支付金额合计(去重): {df_d.drop_duplicates("订单编号")["订单支付金额"].sum():,.2f}')

print('\n--- 汇总表 ---')
print(f'  发货总量合计: {df_s["发货总量"].sum():,}')
print(f'  退货总量合计: {df_s["退货总量"].sum():,}')
print(f'  实际销售量合计: {df_s["实际销售量"].sum():,}')
print(f'  发货总金额合计: {df_s["发货总金额"].sum():,.2f}')
print(f'  退货总金额合计: {df_s["退货总金额"].sum():,.2f}')
print(f'  实际销售额合计: {df_s["实际销售额"].sum():,.2f}')
print(f'  货品总成本合计: {df_s["货品总成本"].sum():,.2f}')
print(f'  退货总成本合计: {df_s["退货总成本"].sum():,.2f}')
print(f'  实际总成本合计: {df_s["实际总成本"].sum():,.2f}')
print(f'  实际总利润合计: {df_s["实际总利润"].sum():,.2f}')

print('\n' + '=' * 80)
print('4. 逐行匹配：明细汇总 vs 汇总表')
print('=' * 80)

merged = detail_agg.merge(summary_agg, on=['店铺', '货品编号'], how='outer', indicator=True)
print(f'匹配结果:')
print(f'  两表都有: {(merged["_merge"] == "both").sum()}')
print(f'  仅明细有: {(merged["_merge"] == "left_only").sum()}')
print(f'  仅汇总有: {(merged["_merge"] == "right_only").sum()}')

# 仅明细有的
only_detail = merged[merged['_merge'] == 'left_only']
if len(only_detail) > 0:
    print(f'\n--- 仅明细表有的组合({len(only_detail)}个) ---')
    cols_show = ['店铺', '货品编号', '明细_货品名称', '明细_发货数量', '明细_发货金额']
    print(only_detail[cols_show].head(20).to_string())

# 仅汇总有的
only_summary = merged[merged['_merge'] == 'right_only']
if len(only_summary) > 0:
    print(f'\n--- 仅汇总表有的组合({len(only_summary)}个) ---')
    cols_show = ['店铺', '货品编号', '汇总_货品名称', '汇总_发货数量', '汇总_发货金额']
    print(only_summary[cols_show].head(20).to_string())

# 都有的 - 对比
both = merged[merged['_merge'] == 'both'].copy()
both['数量差异'] = both['明细_发货数量'] - both['汇总_发货数量']
both['金额差异'] = both['明细_发货金额'] - both['汇总_发货金额']
both['成本差异'] = both['明细_货品总成本'] - both['汇总_货品总成本']

qty_mismatch = both[both['数量差异'] != 0]
amt_mismatch = both[both['金额差异'].abs() > 0.01]
cost_mismatch = both[both['成本差异'].abs() > 0.01]

print(f'\n--- 两表都有的组合: {len(both)}个 ---')
print(f'  数量一致: {len(both) - len(qty_mismatch)}个')
print(f'  数量不一致: {len(qty_mismatch)}个')
print(f'  金额不一致: {len(amt_mismatch)}个')
print(f'  成本不一致: {len(cost_mismatch)}个')

if len(qty_mismatch) > 0:
    print(f'\n--- 数量不一致(前30) ---')
    print(qty_mismatch[['店铺', '货品编号', '明细_货品名称', '明细_发货数量', '汇总_发货数量',
                         '数量差异', '明细_发货金额', '汇总_发货金额', '金额差异']].head(30).to_string())

if len(amt_mismatch) > 0:
    print(f'\n--- 金额不一致(前30) ---')
    print(amt_mismatch[['店铺', '货品编号', '明细_货品名称', '明细_发货金额', '汇总_发货金额',
                         '金额差异', '明细_发货数量', '汇总_发货数量']].head(30).to_string())

# 汇总差异总量
print(f'\n--- 匹配组合差异总量 ---')
print(f'  数量差异合计: {both["数量差异"].sum():,.0f}')
print(f'  金额差异合计: {both["金额差异"].sum():,.2f}')
print(f'  成本差异合计: {both["成本差异"].sum():,.2f}')

print('\n' + '=' * 80)
print('5. 退货数据分析')
print('=' * 80)

# 明细表里是否有负数（退货）
neg_qty = df_d[df_d['货品数量'] < 0]
print(f'--- 明细表中货品数量为负的行 ---')
print(f'  行数: {len(neg_qty)}')
if len(neg_qty) > 0:
    print(f'  订单类型分布: {neg_qty["订单类型"].value_counts().to_dict()}')
    print(f'  货品成交总价合计: {neg_qty["货品成交总价"].sum():,.2f}')
    print(f'  货品数量合计: {neg_qty["货品数量"].sum():,}')
    print(f'  店铺分布: {neg_qty["店铺"].value_counts().to_dict()}')

neg_amt = df_d[df_d['货品成交总价'] < 0]
print(f'\n--- 明细表中货品成交总价为负的行 ---')
print(f'  行数: {len(neg_amt)}')
if len(neg_amt) > 0:
    print(f'  订单类型分布: {neg_amt["订单类型"].value_counts().to_dict()}')
    print(f'  货品成交总价合计: {neg_amt["货品成交总价"].sum():,.2f}')
    print(f'  货品数量合计: {neg_amt["货品数量"].sum():,}')

print(f'\n--- 明细表出库单状态 ---')
if '出库单状态' in df_d.columns:
    print(df_d['出库单状态'].value_counts().to_string())
if '出库状态' in df_d.columns:
    print(f'\n出库状态分布:')
    print(df_d['出库状态'].value_counts().to_string())

# 检查"售后换货"类型的行
print(f'\n--- 售后换货订单分析 ---')
after_sale = df_d[df_d['订单类型'] == '售后换货']
print(f'  行数: {len(after_sale)}')
print(f'  货品数量合计: {after_sale["货品数量"].sum():,}')
print(f'  货品成交总价合计: {after_sale["货品成交总价"].sum():,.2f}')
print(f'  货品数量为负的行: {(after_sale["货品数量"] < 0).sum()}')

print('\n' + '=' * 80)
print('6. 实际销售额校验')
print('=' * 80)

# 明细表: 全部行金额 = 发货金额; 负数行 = 退货
detail_all = df_d['货品成交总价'].sum()
detail_neg = neg_amt['货品成交总价'].sum() if len(neg_amt) > 0 else 0
detail_pos = df_d[df_d['货品成交总价'] >= 0]['货品成交总价'].sum()

print(f'--- 明细表 ---')
print(f'  正数行金额(发货): {detail_pos:,.2f}')
print(f'  负数行金额(退货): {detail_neg:,.2f}')
print(f'  全部行合计: {detail_all:,.2f}')
print(f'  净销售额(正+负): {detail_pos + detail_neg:,.2f}')

print(f'\n--- 汇总表 ---')
print(f'  发货总金额: {df_s["发货总金额"].sum():,.2f}')
print(f'  退货总金额: {df_s["退货总金额"].sum():,.2f}')
print(f'  实际销售额: {df_s["实际销售额"].sum():,.2f}')

print(f'\n--- 差异 ---')
print(f'  发货金额差异(明细正数 - 汇总发货): {detail_pos - df_s["发货总金额"].sum():,.2f}')
print(f'  退货金额差异(明细负数abs - 汇总退货): {abs(detail_neg) - df_s["退货总金额"].sum():,.2f}')
print(f'  净销售差异(明细净额 - 汇总实际): {(detail_pos + detail_neg) - df_s["实际销售额"].sum():,.2f}')

print('\n' + '=' * 80)
print('7. 按店铺对比')
print('=' * 80)

detail_by_store = df_d.groupby('店铺').agg(
    明细_行数=('货品数量', 'count'),
    明细_发货金额=('货品成交总价', 'sum'),
    明细_成本=('货品总成本', 'sum'),
).reset_index()

summary_by_store = df_s.groupby('店铺').agg(
    汇总_发货金额=('发货总金额', 'sum'),
    汇总_退货金额=('退货总金额', 'sum'),
    汇总_实际销售额=('实际销售额', 'sum'),
    汇总_实际利润=('实际总利润', 'sum'),
).reset_index()

store_merged = detail_by_store.merge(summary_by_store, on='店铺', how='outer')
store_merged['金额差异'] = store_merged['明细_发货金额'] - store_merged['汇总_发货金额']
print(store_merged.to_string())
