"""对比新旧旺店通数据文件结构"""
import pandas as pd

# ===== 新文件1: 2607销售出库明细表 =====
f1 = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx'
df1 = pd.read_excel(f1, sheet_name='Sheet1')
print(f'=== 新文件1: 2607销售出库明细表 ===')
print(f'总行数: {len(df1)}  总列数: {len(df1.columns)}')

# 关键字段样本
cols = ['订单编号', '店铺', '订单类型', '商家编码', '货品名称', '货品数量',
        '货品成交价', '货品成交总价', '货品成本', '货品总成本', '订单毛利', '毛利率',
        '仓库', '下单时间', '发货时间']
print(f'\n--- 关键字段样本(前3行) ---')
for idx, row in df1.head(3).iterrows():
    print(f'\nRow {idx}:')
    for c in cols:
        val = row.get(c)
        print(f'  {c}: [{val}] type={type(val).__name__}')

print(f'\n--- 店铺分布 ---')
print(df1['店铺'].value_counts().to_string())
print(f'\n--- 订单类型分布 ---')
print(df1['订单类型'].value_counts().to_string())
print(f'\n--- 仓库分布 ---')
print(df1['仓库'].value_counts().to_string())

# 货品成本检查
cost_col = df1['货品成本'].astype(str)
no_perm = (cost_col == '无权限').sum()
has_cost = df1['货品成本'].notna().sum() - no_perm
print(f'\n--- 货品成本检查 ---')
print(f'  有成本数据: {has_cost} 行')
print(f'  无权限: {no_perm} 行')
print(f'  空值: {df1["货品成本"].isna().sum()} 行')
print(f'  成本值分布(前10):')
print(df1['货品成本'].value_counts().head(10).to_string())

# 毛利率检查
print(f'\n--- 毛利率检查 ---')
print(f'  有毛利率数据: {df1["毛利率"].notna().sum()} 行')
print(f'  毛利率样本(前5): {df1["毛利率"].head(5).tolist()}')

# ===== 对比旧文件字段 =====
f_old = r'C:\Users\jingz\Desktop\IMAX慕咖Sttoke礼盒装销售出库退货明细.xlsx'
df_old_sales = pd.read_excel(f_old, sheet_name='销售明细', nrows=1)
print(f'\n\n=== 旧文件: 销售出库退货明细.xlsx (销售明细Sheet) ===')
print(f'总列数: {len(df_old_sales.columns)}')
old_cols = set(df_old_sales.columns.tolist())
new_cols = set(df1.columns.tolist())

print(f'\n--- 新文件独有字段({len(new_cols - old_cols)}个) ---')
for c in sorted(new_cols - old_cols):
    print(f'  + {c}')

print(f'\n--- 旧文件独有字段({len(old_cols - new_cols)}个) ---')
for c in sorted(old_cols - new_cols):
    print(f'  - {c}')

print(f'\n--- 共同字段({len(new_cols & old_cols)}个) ---')
common = sorted(new_cols & old_cols)
for c in common:
    print(f'  = {c}')

# ===== 新文件2: 货品销售汇总表 =====
f2 = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx'
df2 = pd.read_excel(f2, sheet_name='Sheet1')
print(f'\n\n=== 新文件2: 2607货品销售汇总表 ===')
print(f'总行数: {len(df2)}  总列数: {len(df2.columns)}')
print(f'\n--- 字段列表 ---')
for i, c in enumerate(df2.columns):
    print(f'  {i+1:3d}. {c} (dtype={df2[c].dtype})')

# 汇总表是按店铺+货品维度的汇总
print(f'\n--- 汇总维度分析 ---')
print(f'  店铺数: {df2["店铺"].nunique()}')
print(f'  货品数: {df2["货品编号"].nunique()}')
print(f'  店铺x货品组合数: {df2.groupby(["店铺","货品编号"]).ngroups}')

# 实际销售额总计
print(f'\n--- 金额总计 ---')
print(f'  发货总金额: {df2["发货总金额"].sum():.2f}')
print(f'  退货总金额: {df2["退货总金额"].sum():.2f}')
print(f'  实际销售额: {df2["实际销售额"].sum():.2f}')
print(f'  实际总成本: {df2["实际总成本"].sum():.2f}')
print(f'  实际总利润: {df2["实际总利润"].sum():.2f}')
