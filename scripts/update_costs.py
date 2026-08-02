#!/usr/bin/env python
"""Update product costs from two Excel files into the database.
Updates: products.unit_cost (new column), order_items, sales_summary, orders.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import psycopg2
from decimal import Decimal

# ---- 1. Read both cost files ----
print("=" * 60)
print("Step 1: Reading cost files...")
print("=" * 60)

# File 1: 产品单件成本.xlsx (main cost file, 146 products)
df1 = pd.read_excel(
    r'D:\Users\jingz\Documents\小龙虾分析数据 202604\manus\产品单件成本.xlsx',
    sheet_name='STTOKE'
)
df1 = df1[['货物编码', '产品成本']].copy()
df1.columns = ['sku', 'cost']
df1['sku'] = df1['sku'].astype(str).str.strip()
df1['cost'] = pd.to_numeric(df1['cost'], errors='coerce')
df1 = df1.dropna(subset=['sku', 'cost'])
print(f"File 1 (产品单件成本.xlsx): {len(df1)} products")

# File 2: 副本成本缺失0529-补充.xlsx (supplementary, 56 products)
df2 = pd.read_excel(
    r'D:\Users\jingz\Documents\小龙虾分析数据 202604\20260524\副本成本缺失0529-补充.xlsx',
    header=None, skiprows=1
)
df2.columns = ['sku', 'name', 'type', 'cost']
df2 = df2[df2['sku'].notna() & df2['cost'].notna()].copy()
df2 = df2[~df2['sku'].astype(str).str.startswith('▶')].copy()
df2['sku'] = df2['sku'].astype(str).str.strip()
df2['cost'] = pd.to_numeric(df2['cost'], errors='coerce')
df2 = df2.dropna(subset=['sku', 'cost'])
df2 = df2[['sku', 'cost']]
print(f"File 2 (副本成本缺失0529-补充.xlsx): {len(df2)} products")

# Merge: file2 first, file1 overrides (file1 is the authoritative main cost file)
merged = pd.concat([df2, df1], ignore_index=True)
merged = merged.drop_duplicates(subset='sku', keep='last')
print(f"Total unique SKUs with costs: {len(merged)}")

cost_map = {}
for _, row in merged.iterrows():
    cost_map[row['sku']] = float(row['cost'])

# ---- 2. Connect to database ----
print("\n" + "=" * 60)
print("Step 2: Connecting to database...")
print("=" * 60)

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='sales_analysis', user='postgres',
    password='Maoxitrading123'
)
cur = conn.cursor()

# ---- 3. Add unit_cost column to products if not exists ----
print("\n" + "=" * 60)
print("Step 3: Adding unit_cost to products table...")
print("=" * 60)

cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name='products' AND column_name='unit_cost'
""")
if cur.fetchone() is None:
    cur.execute("ALTER TABLE products ADD COLUMN unit_cost numeric(12,4)")
    conn.commit()
    print("Added unit_cost column to products table")
else:
    print("unit_cost column already exists")

# ---- 4. Update products.unit_cost ----
print("\n" + "=" * 60)
print("Step 4: Updating products.unit_cost...")
print("=" * 60)

cur.execute("SELECT id, sku, product_name, unit_cost FROM products ORDER BY sku")
db_products = cur.fetchall()
print(f"Database products: {len(db_products)}")

updated = 0
newly_set = 0
no_match = 0
unchanged = 0
changes = []

for prod_id, sku, name, old_cost in db_products:
    sku_str = str(sku).strip() if sku else ""
    if sku_str in cost_map:
        new_cost = cost_map[sku_str]
        old_cost_val = float(old_cost) if old_cost is not None else None
        
        if old_cost_val is None:
            cur.execute(
                "UPDATE products SET unit_cost = %s WHERE id = %s",
                (new_cost, prod_id)
            )
            newly_set += 1
            changes.append((sku_str, name, None, new_cost, 'NEW'))
        elif abs(old_cost_val - new_cost) > 0.001:
            cur.execute(
                "UPDATE products SET unit_cost = %s WHERE id = %s",
                (new_cost, prod_id)
            )
            updated += 1
            changes.append((sku_str, name, old_cost_val, new_cost, 'CHANGED'))
        else:
            unchanged += 1
    else:
        no_match += 1

conn.commit()

print(f"\nResults:")
print(f"  Newly set (was NULL):  {newly_set}")
print(f"  Updated (cost changed): {updated}")
print(f"  Unchanged (same cost): {unchanged}")
print(f"  No match in cost files: {no_match}")

if changes:
    print(f"\n{'='*100}")
    print(f"Changed/New products ({len(changes)}):")
    print(f"{'='*100}")
    print(f"{'SKU':<25} {'Old':>10} {'New':>10} {'Action':<8} Name")
    print("-" * 100)
    for sku, name, old, new, action in sorted(changes, key=lambda x: x[0]):
        old_str = f"{old:.2f}" if old is not None else "NULL"
        name_short = str(name)[:40] if name else ""
        print(f"{sku:<25} {old_str:>10} {new:>10.2f} {action:<8} {name_short}")

# ---- 5. Update order_items costs ----
print("\n" + "=" * 60)
print("Step 5: Updating order_items costs...")
print("=" * 60)

# Get before totals
cur.execute("SELECT count(*), sum(total_cost) FROM order_items")
r = cur.fetchone()
print(f"Before: {r[0]} items, total_cost = {r[1]}")

# Update unit_cost and total_cost from products
cur.execute("""
    UPDATE order_items oi
    SET 
        unit_cost = p.unit_cost,
        total_cost = oi.quantity * p.unit_cost
    FROM products p
    WHERE oi.product_id = p.id AND p.unit_cost IS NOT NULL
""")
print(f"Updated {cur.rowcount} order_items rows")
conn.commit()

cur.execute("SELECT count(*), sum(total_cost) FROM order_items")
r = cur.fetchone()
print(f"After:  {r[0]} items, total_cost = {r[1]}")

# ---- 6. Recalculate orders.gross_profit ----
print("\n" + "=" * 60)
print("Step 6: Recalculating orders.gross_profit...")
print("=" * 60)

cur.execute("SELECT count(*), sum(gross_profit) FROM orders")
r = cur.fetchone()
print(f"Before: {r[0]} orders, gross_profit = {r[1]}")

cur.execute("""
    UPDATE orders o
    SET gross_profit = o.total_amount - COALESCE(
        (SELECT SUM(oi.total_cost) FROM order_items oi WHERE oi.order_id = o.id), 0
    )
""")
print(f"Updated {cur.rowcount} orders")
conn.commit()

cur.execute("""
    UPDATE orders 
    SET gross_profit_rate = CASE 
        WHEN total_amount > 0 THEN gross_profit / total_amount 
        ELSE 0 
    END
""")
conn.commit()

cur.execute("SELECT count(*), sum(gross_profit) FROM orders")
r = cur.fetchone()
print(f"After:  {r[0]} orders, gross_profit = {r[1]}")

# ---- 7. Recalculate sales_summary costs ----
print("\n" + "=" * 60)
print("Step 7: Recalculating sales_summary costs...")
print("=" * 60)

cur.execute("""
    SELECT sum(ship_qty), sum(return_qty), sum(net_qty),
           sum(total_cost), sum(return_cost), sum(net_cost),
           sum(net_amount), sum(net_profit)
    FROM sales_summary
""")
r = cur.fetchone()
print(f"Before: ship_qty={r[0]}, net_qty={r[2]}")
print(f"        total_cost={r[3]}, net_cost={r[5]}, net_amount={r[6]}, net_profit={r[7]}")

# Get product unit costs as a dict for manual calculation
cur.execute("SELECT id, unit_cost FROM products WHERE unit_cost IS NOT NULL")
prod_costs = {str(r[0]): float(r[1]) for r in cur.fetchall()}

# Update sales_summary row by row (total_cost, return_cost, net_cost, ship_profit, net_profit)
cur.execute("SELECT id, product_id, ship_qty, return_qty, net_qty, ship_amount, return_amount, net_amount, commission_cost FROM sales_summary")
rows = cur.fetchall()
updated_count = 0
for row in rows:
    ss_id, prod_id, ship_qty, return_qty, net_qty, ship_amt, return_amt, net_amt, commission = row
    prod_id_str = str(prod_id)
    if prod_id_str in prod_costs:
        uc = prod_costs[prod_id_str]
        new_total_cost = ship_qty * uc
        new_return_cost = return_qty * uc
        new_net_cost = net_qty * uc
        comm = float(commission) if commission else 0
        new_ship_profit = float(ship_amt) - new_total_cost - comm
        new_net_profit = float(net_amt) - new_net_cost - comm
        
        cur.execute("""
            UPDATE sales_summary 
            SET total_cost = %s, return_cost = %s, net_cost = %s,
                ship_profit = %s, net_profit = %s
            WHERE id = %s
        """, (new_total_cost, new_return_cost, new_net_cost, new_ship_profit, new_net_profit, ss_id))
        updated_count += 1

conn.commit()
print(f"Updated {updated_count} sales_summary rows")

cur.execute("""
    SELECT sum(ship_qty), sum(return_qty), sum(net_qty),
           sum(total_cost), sum(return_cost), sum(net_cost),
           sum(net_amount), sum(net_profit)
    FROM sales_summary
""")
r = cur.fetchone()
print(f"After:  ship_qty={r[0]}, net_qty={r[2]}")
print(f"        total_cost={r[3]}, net_cost={r[5]}, net_amount={r[6]}, net_profit={r[7]}")

conn.close()

# ---- 8. Summary ----
print("\n" + "=" * 60)
print("DONE! All costs updated successfully.")
print("=" * 60)
print(f"\nProducts updated: {newly_set + updated} (new: {newly_set}, changed: {updated})")
print(f"Products unchanged: {unchanged}")
print(f"Products without cost match: {no_match}")
print(f"\nKey metrics after update:")
print(f"  Total net_cost (actual cost):    {r[5]}")
print(f"  Total net_amount (actual sales): {r[6]}")
print(f"  Total net_profit (actual profit): {r[7]}")
if r[6] and r[5]:
    margin = (float(r[7]) / float(r[6])) * 100
    print(f"  Net profit margin: {margin:.2f}%")
