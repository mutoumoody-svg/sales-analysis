#!/usr/bin/env python3
"""从 trade_daily JSON 生成店铺日报 HTML."""
import json
import sys
from datetime import datetime

src = sys.argv[1] if len(sys.argv) > 1 else "screenshots/muka_aug.json"
out = sys.argv[2] if len(sys.argv) > 2 else "screenshots/muka_aug_report.html"

with open(src, encoding="utf-8") as f:
    d = json.load(f)

daily = d["daily"]
skus = d["sku_summary"]
shop_filter = d.get("shop_filter") or "全部"

# 店铺汇总
shops = {}
for date, v in daily.items():
    for s, sv in v["shops"].items():
        if s not in shops:
            shops[s] = {"count": 0, "paid": 0.0}
        shops[s]["count"] += sv["count"]
        shops[s]["paid"] += sv["paid"]
shops = sorted(shops.items(), key=lambda x: -x[1]["paid"])

total_cnt = sum(v["order_count"] for v in daily.values())
total_paid = sum(v["paid"] for v in daily.values())
days = len(daily)
avg_paid = total_paid / days if days else 0

dates = sorted(daily.keys())
best = max(daily.items(), key=lambda x: x[1]["paid"])

def color_pos(s): return f'<span style="color:#d4380d;font-weight:600">{s}</span>'
def fmt_money(x): return f"¥{x:,.0f}"

rows = []
prev_paid = None
for date in dates:
    v = daily[date]
    dod = ""
    if prev_paid is not None and prev_paid > 0:
        pct = (v["paid"] - prev_paid) / prev_paid * 100
        sign = "+" if pct >= 0 else ""
        cls = "#cf1322" if pct >= 0 else "#3c8436"
        dod = f'<span style="color:{cls}">{sign}{pct:.1f}%</span>'
    prev_paid = v["paid"]
    shop_cells = ""
    for s, _ in shops:
        sv = v["shops"].get(s)
        if sv:
            shop_cells += f"<td>{sv['count']} / {fmt_money(sv['paid'])}</td>"
        else:
            shop_cells += "<td>—</td>"
    refund_info = ""
    if v["refund_full"] or v["refund_part"]:
        refund_info = f'{v["refund_full"]}全退/{v["refund_part"]}部分'
    rows.append(f"""<tr>
<td>{date[5:]}</td><td style="text-align:right">{v['order_count']}</td>
<td style="text-align:right;font-weight:600">{fmt_money(v['paid'])}</td>
<td style="text-align:right">{dod}</td>
{shop_cells}
<td style="text-align:center;font-size:12px">{refund_info}</td></tr>""")

shop_head = "".join(f"<th style='white-space:nowrap'>{s.replace('慕咖官方旗舰店','旗舰店').replace('慕咖','')}<br><small>单数 / 实付</small></th>" for s, _ in shops)

sku_rows = []
for i, (sku, v) in enumerate(list(skus.items())[:20]):
    sku_rows.append(f"""<tr><td>{i+1}</td><td><code>{sku}</code></td><td>{v['name']}</td>
<td style="text-align:right">{v['qty']:.0f}</td>
<td style="text-align:right;font-weight:600">{fmt_money(v['amount'])}</td>
<td style="text-align:right">{v['amount']/max(v['qty'],1):,.0f}</td>
<td style="text-align:right">{v['orders']}</td></tr>""")

shop_rows = []
for s, v in shops:
    share = v["paid"] / total_paid * 100 if total_paid else 0
    shop_rows.append(f"""<tr><td>{s}</td>
<td style="text-align:right">{v['count']}</td>
<td style="text-align:right;font-weight:600">{fmt_money(v['paid'])}</td>
<td style="text-align:right">{v['count']/total_cnt*100:.1f}%</td>
<td style="text-align:right">{fmt_money(v['paid']/v['count'])}</td>
<td>
<div style="background:#e6f4ff;border-radius:4px;height:16px;position:relative">
<div style="background:#1677ff;width:{share:.1f}%;height:16px;border-radius:4px"></div>
<span style="position:absolute;left:8px;line-height:16px;font-size:12px;color:#333">{share:.1f}%</span>
</div></td></tr>""")

max_paid = max(v["paid"] for v in daily.values())
bars = ""
for date in dates:
    v = daily[date]
    h = v["paid"] / max_paid * 140
    bars += f"""<div style="display:inline-block;width:26px;text-align:center;vertical-align:bottom;margin:0 1px">
<div style="background:linear-gradient(180deg,#4096ff,#1677ff);width:20px;height:{h:.0f}px;margin:0 auto;border-radius:3px 3px 0 0"></div>
<div style="font-size:10px;color:#666;margin-top:3px">{date[8:]}</div></div>"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>慕咖店铺日报 · {dates[0]} ~ {dates[-1]}</title>
<style>
body{{font-family:-apple-system,'Microsoft YaHei',sans-serif;margin:0;background:#f5f5f5;color:#333}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px 16px}}
h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:#888;font-size:13px;margin-bottom:20px}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.kpi{{background:#fff;border-radius:10px;padding:16px 20px;flex:1;min-width:150px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi .label{{font-size:12px;color:#888}}
.kpi .value{{font-size:26px;font-weight:700;margin-top:4px}}
.card{{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.06);margin-bottom:20px}}
h2{{font-size:16px;margin:0 0 14px;border-left:4px solid #1677ff;padding-left:8px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#fafafa;padding:8px 6px;border-bottom:2px solid #eee;text-align:right;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}
td{{padding:7px 6px;border-bottom:1px solid #f0f0f0;text-align:right}}
tr:hover td{{background:#f5f8ff}}
code{{background:#f5f5f5;padding:1px 5px;border-radius:3px;font-size:12px}}
.note{{background:#fffbe6;border:1px solid #ffe58f;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:20px}}
</style></head><body><div class="wrap">
<h1>慕咖店铺日报</h1>
<div class="sub">{dates[0]} ~ {dates[-1]}（{days}天） · 数据源：旺店通API实时抓取 · 生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>

<div class="note">⚠️ 本报告不含天猫、拼多多订单（旺店通API不返回该平台数据），也不含微信视频号以外的淘系店铺。</div>

<div class="kpis">
<div class="kpi"><div class="label">总实付</div><div class="value" style="color:#1677ff">{fmt_money(total_paid)}</div></div>
<div class="kpi"><div class="label">总订单数</div><div class="value">{total_cnt:,}</div></div>
<div class="kpi"><div class="label">日均实付</div><div class="value">{fmt_money(avg_paid)}</div></div>
<div class="kpi"><div class="label">客单价</div><div class="value">{fmt_money(total_paid/max(total_cnt,1))}</div></div>
<div class="kpi"><div class="label">峰值日</div><div class="value" style="font-size:18px">{best[0][5:]}<br><small>{fmt_money(best[1]['paid'])}</small></div></div>
</div>

<div class="card"><h2>店铺占比</h2>
<table><thead><tr><th>店铺</th><th>订单数</th><th>实付金额</th><th>订单占比</th><th>客单价</th><th>金额占比</th></tr></thead>
<tbody>{''.join(shop_rows)}</tbody></table></div>

<div class="card"><h2>每日趋势</h2>
<div style="text-align:center;padding:8px 0">{bars}</div>
<table style="margin-top:14px"><thead><tr><th>日期</th><th>订单数</th><th>实付</th><th>环比</th>{shop_head}<th>退款</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
<tfoot><tr style="background:#fafafa;font-weight:700"><td>合计</td><td>{total_cnt:,}</td><td>{fmt_money(total_paid)}</td><td></td>{''.join(f'<td>{v["count"]} / {fmt_money(v["paid"])}</td>' for _, v in shops)}<td></td></tr></tfoot></table></div>

<div class="card"><h2>Top 20 SKU（{len(skus)}个SKU有动销）</h2>
<table><thead><tr><th>#</th><th>SKU</th><th>商品名称</th><th>件数</th><th>实付金额</th><th>均价</th><th>订单数</th></tr></thead>
<tbody>{''.join(sku_rows)}</tbody></table></div>

</div></body></html>"""

with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"已生成: {out}")
print(f"总览: {total_cnt}单 {fmt_money(total_paid)} 均日{fmt_money(avg_paid)}")
for s, v in shops:
    print(f"  {s}: {v['count']}单 {fmt_money(v['paid'])}")
