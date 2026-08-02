"""验证差异根因：空值导致groupby丢数据"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

f_detail = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607销售出库明细表.xlsx'
df_d = pd.read_excel(f_detail, sheet_name='Sheet1')

# 检查 商家编码 和 货品编号 的空值
print('=== 空值检查 ===')
print(f'总行数: {len(df_d)}')
print(f'商家编码 空值: {df_d["商家编码"].isna().sum()}')
print(f'货品编号 空值: {df_d["货品编号"].isna().sum()}')

# 商家编码为空的行的金额
na_rows = df_d[df_d['商家编码'].isna()]
print(f'\n商家编码为空的行:')
print(f'  行数: {len(na_rows)}')
print(f'  货品成交总价: {na_rows["货品成交总价"].sum():,.2f}')
print(f'  货品数量: {na_rows["货品数量"].sum():,}')
print(f'  店铺分布: {na_rows["店铺"].value_counts().to_dict()}')
print(f'  订单类型分布: {na_rows["订单类型"].value_counts().to_dict()}')

# 货品编号为空但商家编码不为空的行
na_code_only = df_d[df_d['货品编号'].isna() & df_d['商家编码'].notna()]
print(f'\n货品编号为空但商家编码有值:')
print(f'  行数: {len(na_code_only)}')

# 用 货品编号 重新汇总
print(f'\n=== 用 货品编号 代替 商家编码 重新汇总 ===')
detail_agg2 = df_d[df_d['货品编号'].notna()].groupby(['店铺', '货品编号']).agg(
    发货数量=('货品数量', 'sum'),
    发货金额=('货品成交总价', 'sum'),
    货品总成本=('货品总成本', 'sum'),
).reset_index()
print(f'货品编号非空的组合数: {len(detail_agg2)}')
print(f'货品编号非空的发货金额: {detail_agg2["发货金额"].sum():,.2f}')

# 直接sum vs groupby后sum
print(f'\n=== 直接sum vs groupby后sum ===')
print(f'直接 sum(货品成交总价): {df_d["货品成交总价"].sum():,.2f}')
print(f'商家编码非空行 sum: {df_d[df_d["商家编码"].notna()]["货品成交总价"].sum():,.2f}')
print(f'货品编号非空行 sum: {df_d[df_d["货品编号"].notna()]["货品成交总价"].sum():,.2f}')

# 两个编号的关系
print(f'\n=== 商家编码 vs 货品编号 ===')
both_notna = df_d[df_d['商家编码'].notna() & df_d['货品编号'].notna()]
print(f'两者都有值的行数: {len(both_notna)}')
# 检查两者是否相同
same = (both_notna['商家编码'] == both_notna['货品编号']).sum()
diff = len(both_notna) - same
print(f'  两者相同: {same}')
print(f'  两者不同: {diff}')
if diff > 0:
    sample = both_notna[both_notna['商家编码'] != both_notna['货品编号']].head(10)
    print(f'  样本:')
    for _, r in sample.iterrows():
        print(f'    商家编码: [{r["商家编码"]}] / 货品编号: [{r["货品编号"]}] / 货品名称: [{r["货品名称"]}]')

# 汇总表用的什么编号
f_summary = r'D:\Users\jingz\Documents\2608库存销售分析系统\2607货品销售汇总表.xlsx'
df_s = pd.read_excel(f_summary, sheet_name='Sheet1')
df_s_clean = df_s[df_s['货品编号'].notna() & (df_s['店铺'] != '合计:')].copy()

print(f'\n=== 汇总表货品编号检查 ===')
print(f'汇总表货品编号样本(前5): {df_s_clean["货品编号"].head(5).tolist()}')
print(f'汇总表货品编号唯一值数: {df_s_clean["货品编号"].nunique()}')

# 检查汇总表的货品编号是否在明细表的商家编码中
detail_codes = set(df_d['商家编码'].dropna().unique())
summary_codes = set(df_s_clean['货品编号'].dropna().unique())
print(f'\n明细表商家编码唯一值: {len(detail_codes)}')
print(f'汇总表货品编号唯一值: {len(summary_codes)}')
print(f'交集: {len(detail_codes & summary_codes)}')
print(f'仅汇总有: {len(summary_codes - detail_codes)}')
print(f'仅明细有: {len(detail_codes - summary_codes)}')

# 检查汇总表的货品编号是否在明细表的"货品编号"字段中
detail_codes2 = set(df_d['货品编号'].dropna().unique())
print(f'\n明细表货品编号唯一值: {len(detail_codes2)}')
print(f'交集(汇总 vs 明细货品编号): {len(detail_codes2 & summary_codes)}')
