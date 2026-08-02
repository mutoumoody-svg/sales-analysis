"""交叉验证 v3 - 聚焦差异分析"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

f_detail = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx'
f_summary = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx'

df_d = pd.read_excel(f_detail, sheet_name='Sheet1')
df_s = pd.read_excel(f_summary, sheet_name='Sheet1')

# 清洗汇总表：去掉合计行和空货品编号行
print('=== 汇总表数据清洗 ===')
print(f'原始行数: {len(df_s)}')
df_s_clean = df_s[df_s['货品编号'].notna() & (df_s['店铺'] != '合计:')].copy()
print(f'去掉合计行和空货品行后: {len(df_s_clean)}')

# 明细汇总
detail_agg = df_d.groupby(['店铺', '商家编码']).agg(
    明细_发货数量=('货品数量', 'sum'),
    明细_发货金额=('货品成交总价', 'sum'),
    明细_货品总成本=('货品总成本', 'sum'),
    明细_货品名称=('货品名称', 'first'),
    明细_行数=('货品数量', 'count'),
).reset_index()
detail_agg.rename(columns={'商家编码': '货品编号'}, inplace=True)

summary_agg = df_s_clean[['店铺', '货品编号', '货品名称', '发货总量', '退货总量', '实际销售量',
                     '发货总金额', '退货总金额', '实际销售额', '货品总成本', '退货总成本',
                     '实际总成本', '实际总利润']].copy()
summary_agg.columns = ['店铺', '货品编号', '汇总_货品名称', '汇总_发货数量', '汇总_退货数量',
                        '汇总_实际销售量', '汇总_发货金额', '汇总_退货金额', '汇总_实际销售额',
                        '汇总_货品总成本', '汇总_退货总成本', '汇总_实际总成本', '汇总_实际总利润']

merged = detail_agg.merge(summary_agg, on=['店铺', '货品编号'], how='outer', indicator=True)

print(f'\n=== 匹配结果(清洗后) ===')
print(f'  两表都有: {(merged["_merge"] == "both").sum()}')
print(f'  仅明细有: {(merged["_merge"] == "left_only").sum()}')
print(f'  仅汇总有: {(merged["_merge"] == "right_only").sum()}')

# 仅汇总有
only_summary = merged[merged['_merge'] == 'right_only']
if len(only_summary) > 0:
    print(f'\n--- 仅汇总表有的组合({len(only_summary)}个) ---')
    print(only_summary[['店铺', '货品编号', '汇总_货品名称', '汇总_发货数量', '汇总_发货金额']].to_string())

# 仅明细有
only_detail = merged[merged['_merge'] == 'left_only']
if len(only_detail) > 0:
    print(f'\n--- 仅明细表有的组合({len(only_detail)}个) ---')
    print(only_detail[['店铺', '货品编号', '明细_货品名称', '明细_发货数量', '明细_发货金额']].to_string())

# 匹配的组合
both = merged[merged['_merge'] == 'both'].copy()
both['数量差异'] = both['明细_发货数量'] - both['汇总_发货数量']
both['金额差异'] = both['明细_发货金额'] - both['汇总_发货金额']
both['成本差异'] = both['明细_货品总成本'] - both['汇总_货品总成本']

qty_mismatch = both[both['数量差异'] != 0]
amt_mismatch = both[both['金额差异'].abs() > 0.01]
cost_mismatch = both[both['成本差异'].abs() > 0.01]

print(f'\n=== 匹配组合差异 ===')
print(f'  共{len(both)}个组合')
print(f'  数量不一致: {len(qty_mismatch)}个')
print(f'  金额不一致: {len(amt_mismatch)}个')
print(f'  成本不一致: {len(cost_mismatch)}个')
print(f'  数量差异合计: {both["数量差异"].sum():,.0f}')
print(f'  金额差异合计: {both["金额差异"].sum():,.2f}')
print(f'  成本差异合计: {both["成本差异"].sum():,.2f}')

if len(qty_mismatch) > 0:
    print(f'\n--- 数量不一致(全部) ---')
    print(qty_mismatch[['店铺', '货品编号', '明细_货品名称', '明细_发货数量', '汇总_发货数量',
                         '数量差异', '明细_发货金额', '汇总_发货金额', '金额差异']].to_string())

# 退货分析
print(f'\n=== 退货数据分析 ===')
neg_qty = df_d[df_d['货品数量'] < 0]
neg_amt = df_d[df_d['货品成交总价'] < 0]
print(f'货品数量为负的行: {len(neg_qty)}')
print(f'货品成交总价为负的行: {len(neg_amt)}')

if len(neg_amt) > 0:
    print(f'负金额行订单类型: {neg_amt["订单类型"].value_counts().to_dict()}')
    print(f'负金额行货品成交总价: {neg_amt["货品成交总价"].sum():,.2f}')
    print(f'负金额行货品数量: {neg_amt["货品数量"].sum():,}')
    print(f'负金额行店铺: {neg_amt["店铺"].value_counts().to_dict()}')

# 售后换货
print(f'\n=== 售后换货订单 ===')
after_sale = df_d[df_d['订单类型'] == '售后换货']
print(f'行数: {len(after_sale)}')
print(f'货品数量合计: {after_sale["货品数量"].sum():,}')
print(f'货品成交总价: {after_sale["货品成交总价"].sum():,.2f}')
print(f'负数行: {(after_sale["货品数量"] < 0).sum()}, 负金额行: {(after_sale["货品成交总价"] < 0).sum()}')

# 实际销售额校验
print(f'\n=== 实际销售额校验 ===')
detail_pos = df_d[df_d['货品成交总价'] >= 0]['货品成交总价'].sum()
detail_neg = neg_amt['货品成交总价'].sum() if len(neg_amt) > 0 else 0
print(f'明细表正数行(发货): {detail_pos:,.2f}')
print(f'明细表负数行(退货): {detail_neg:,.2f}')
print(f'明细表净额: {detail_pos + detail_neg:,.2f}')
print(f'汇总表发货总金额: {df_s_clean["发货总金额"].sum():,.2f}')
print(f'汇总表退货总金额: {df_s_clean["退货总金额"].sum():,.2f}')
print(f'汇总表实际销售额: {df_s_clean["实际销售额"].sum():,.2f}')
print(f'发货金额差异: {detail_pos - df_s_clean["发货总金额"].sum():,.2f}')
print(f'退货金额差异: {abs(detail_neg) - df_s_clean["退货总金额"].sum():,.2f}')
print(f'净额差异: {(detail_pos + detail_neg) - df_s_clean["实际销售额"].sum():,.2f}')

# 按店铺对比
print(f'\n=== 按店铺对比 ===')
detail_by_store = df_d.groupby('店铺').agg(
    明细_行数=('货品数量', 'count'),
    明细_发货金额=('货品成交总价', 'sum'),
    明细_成本=('货品总成本', 'sum'),
).reset_index()

summary_by_store = df_s_clean.groupby('店铺').agg(
    汇总_发货金额=('发货总金额', 'sum'),
    汇总_退货金额=('退货总金额', 'sum'),
    汇总_实际销售额=('实际销售额', 'sum'),
    汇总_实际利润=('实际总利润', 'sum'),
).reset_index()

store_merged = detail_by_store.merge(summary_by_store, on='店铺', how='outer')
store_merged['金额差异'] = store_merged['明细_发货金额'] - store_merged['汇总_发货金额']
store_merged = store_merged.sort_values('明细_发货金额', ascending=False)
print(store_merged.to_string())

# 货品编号大小写问题检查
print(f'\n=== 货品编号大小写检查 ===')
detail_codes = set(df_d['商家编码'].dropna().unique())
summary_codes = set(df_s_clean['货品编号'].dropna().unique())
# 找出仅大小写不同的
detail_lower = {c.lower(): c for c in detail_codes}
summary_lower = {c.lower(): c for c in summary_codes}
common_lower = set(detail_lower.keys()) & set(summary_lower.keys())
case_issues = [(detail_lower[c], summary_lower[c]) for c in common_lower if detail_lower[c] != summary_lower[c]]
print(f'大小写不一致的货品编号: {len(case_issues)}个')
for d, s in case_issues[:10]:
    print(f'  明细: [{d}] vs 汇总: [{s}]')
