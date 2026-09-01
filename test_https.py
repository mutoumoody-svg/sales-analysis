import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE = "https://fenxi.riverline.com.cn"

tests = [
    ("Frontend (HTML)", f"{BASE}/"),
    ("Sales Overview", f"{BASE}/api/v1/sales/overview"),
    ("Profit Summary", f"{BASE}/api/v1/profit/summary"),
    ("Inventory Health", f"{BASE}/api/v1/inventory/health"),
    ("CEO Report", f"{BASE}/api/v1/agents/ceo-report"),
    ("ABC Analysis", f"{BASE}/api/v1/analysis/abc"),
    ("Brand List", f"{BASE}/api/v1/sales/brands"),
]

print("=" * 60)
print("  fenxi.riverline.com.cn HTTPS 端到端测试")
print("=" * 60)

all_pass = True
for name, url in tests:
    try:
        r = urllib.request.urlopen(url, context=ctx, timeout=15)
        body = r.read()
        status = f"HTTP {r.status}"
        if "/api/" in url:
            data = json.loads(body)
            if "status" in data:
                extra = f"status={data['status']}"
                if "data" in data:
                    d = data["data"]
                    if "total_revenue" in d:
                        extra += f", revenue={d['total_revenue']}"
                    elif "total_profit" in d:
                        extra += f", profit={d['total_profit']}"
                    elif "health_score" in d:
                        extra += f", health={d['health_score']}"
                    elif "overall_status" in d:
                        extra += f", overall={d['overall_status']}"
            else:
                extra = str(list(data.keys())[:3])
            print(f"  [PASS] {name:20s} {status} ({len(body)} bytes) -> {extra}")
        else:
            print(f"  [PASS] {name:20s} {status} ({len(body)} bytes)")
    except Exception as e:
        print(f"  [FAIL] {name:20s} ERROR - {e}")
        all_pass = False

print("=" * 60)
if all_pass:
    print("  ALL TESTS PASSED")
else:
    print("  SOME TESTS FAILED")
print("=" * 60)
