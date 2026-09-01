import json, glob, os
files = sorted(glob.glob('/opt/kucun/output/daily_outbound/*.json'))
target_skus = {"NEWBNMGO1050-250","NEWBNMGO100","NEWBNMGO550-250","NEWNBNMGO300-250"}
agg = {s: {"qty":0,"sell":0.0,"cost":0.0,"per_unit_cost_samples":[]} for s in target_skus}
for f in files[-7:]:
    try:
        d = json.load(open(f))
    except: continue
    date = os.path.basename(f).replace('.json','')
    for item in d.get("details", []):
        sn = item.get("spec_no")
        if sn in target_skus:
            qty = item.get("quantity", 0) or 0
            sell = item.get("total_sell_amount", 0) or 0
            cost = item.get("total_cost_amount", 0) or 0
            agg[sn]["qty"] += qty
            agg[sn]["sell"] += sell
            agg[sn]["cost"] += cost
            if qty > 0:
                agg[sn]["per_unit_cost_samples"].append(round(cost/qty, 2))
print(f"近7天汇总（{files[-7][-15:-5]} ~ {files[-1][-15:-5]}）：")
for sn, v in agg.items():
    avg_unit_cost = v["cost"]/v["qty"] if v["qty"] else 0
    avg_unit_sell = v["sell"]/v["qty"] if v["qty"] else 0
    print(f"  {sn}: qty={v['qty']} sell={v['sell']:,.2f} cost={v['cost']:,.2f} | 单件售价={avg_unit_sell:,.2f} 单件成本={avg_unit_cost:,.2f} 成本样本={v['per_unit_cost_samples']}")