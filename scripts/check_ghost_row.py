"""检查那行幽灵数据"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

f_detail = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx'
df_d = pd.read_excel(f_detail, sheet_name='Sheet1')

# 找到商家编码为空的那行
na_row = df_d[df_d['商家编码'].isna()]
print(f'=== 幽灵行(商家编码为空) ===')
print(f'行索引: {na_row.index.tolist()}')
print(f'\n所有字段值:')
for col in df_d.columns:
    val = na_row.iloc[0][col]
    if pd.notna(val):
        print(f'  {col}: [{val}] (type={type(val).__name__})')

# 看这行前后各2行
idx = na_row.index[0]
print(f'\n=== 前后行上下文(行{idx-2}到{idx+2}) ===')
context_cols = ['订单编号', '店铺', '订单类型', '商家编码', '货品编号', '货品名称',
                '货品数量', '货品成交总价', '货品总成本', '下单时间']
for i in range(max(0, idx-2), min(len(df_d), idx+3)):
    row = df_d.iloc[i]
    marker = ' >>> 幽灵行' if i == idx else ''
    print(f'  行{i}: 订单号=[{row["订单编号"]}] 店铺=[{row["店铺"]}] 编码=[{row["商家编码"]}] '
          f'名称=[{row["货品名称"]}] 数量=[{row["货品数量"]}] 金额=[{row["货品成交总价"]}]{marker}')

# 检查是否是最后一行
print(f'\n=== 行位置 ===')
print(f'总行数: {len(df_d)}')
print(f'幽灵行位置: {idx} (倒数第{len(df_d) - idx}行)')

# 去掉这行后重新汇总
print(f'\n=== 去掉幽灵行后的总量 ===')
df_clean = df_d[df_d['商家编码'].notna()].copy()
print(f'行数: {len(df_clean)}')
print(f'货品成交总价: {df_clean["货品成交总价"].sum():,.2f}')
print(f'货品数量: {df_clean["货品数量"].sum():,}')
print(f'货品总成本: {df_clean["货品总成本"].sum():,.2f}')

# 重新和汇总表对比
f_summary = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx'
df_s = pd.read_excel(f_summary, sheet_name='Sheet1')
df_s_clean = df_s[df_s['货品编号'].notna() & (df_s['店铺'] != '合计:')].copy()

print(f'\n=== 去掉幽灵行后 vs 汇总表 ===')
print(f'明细表发货金额: {df_clean["货品成交总价"].sum():,.2f}')
print(f'汇总表发货金额: {df_s_clean["发货总金额"].sum():,.2f}')
print(f'差异: {df_clean["货品成交总价"].sum() - df_s_clean["发货总金额"].sum():,.2f}')

print(f'\n明细表货品数量: {df_clean["货品数量"].sum():,}')
print(f'汇总表发货总量: {df_s_clean["发货总量"].sum():,}')
print(f'差异: {df_clean["货品数量"].sum() - df_s_clean["发货总量"].sum():,}')

print(f'\n明细表货品总成本: {df_clean["货品总成本"].sum():,.2f}')
print(f'汇总表货品总成本: {df_s_clean["货品总成本"].sum():,.2f}')
print(f'差异: {df_clean["货品总成本"].sum() - df_s_clean["货品总成本"].sum():,.2f}')

# 重新逐行匹配
detail_agg = df_clean.groupby(['店铺', '商家编码']).agg(
    明细_发货数量=('货品数量', 'sum'),
    明细_发货金额=('货品成交总价', 'sum'),
    明细_货品总成本=('货品总成本', 'sum'),
    明细_货品名称=('货品名称', 'first'),
).reset_index()
detail_agg.rename(columns={'商家编码': '货品编号'}, inplace=True)

summary_agg = df_s_clean[['店铺', '货品编号', '发货总量', '退货总量', '实际销售量',
                     '发货总金额', '退货总金额', '实际销售额', '货品总成本', '退货总成本',
                     '实际总成本', '实际总利润']].copy()
summary_agg.columns = ['店铺', '货品编号', '汇总_发货数量', '汇总_退货数量',
                        '汇总_实际销售量', '汇总_发货金额', '汇总_退货金额', '汇总_实际销售额',
                        '汇总_货品总成本', '汇总_退货总成本', '汇总_实际总成本', '汇总_实际总利润']

merged = detail_agg.merge(summary_agg, on=['店铺', '货品编号'], how='outer', indicator=True)
both = merged[merged['_merge'] == 'both'].copy()
both['数量差异'] = both['明细_发货数量'] - both['汇总_发货数量']
both['金额差异'] = both['明细_发货金额'] - both['汇总_发货金额']

qty_mm = both[both['数量差异'] != 0]
amt_mm = both[both['金额差异'].abs() > 0.01]
print(f'\n=== 去幽灵行后逐行匹配 ===')
print(f'两表都有: {(merged["_merge"] == "both").sum()}')
print(f'仅明细: {(merged["_merge"] == "left_only").sum()}')
print(f'仅汇总: {(merged["_merge"] == "right_only").sum()}')
print(f'数量不一致: {len(qty_mm)}')
print(f'金额不一致: {len(amt_mm)}')
print(f'数量差异合计: {both["数量差异"].sum():,.0f}')
print(f'金额差异合计: {both["金额差异"].sum():,.2f}')
