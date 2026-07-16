import sys, os, json, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

BASE = "http://127.0.0.1:8000/api/v1"
TOKEN = settings.app_secret_key
passed = 0
failed = 0


def req(method, path, body=None):
    url = (BASE + path).replace(" ", "%20")
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + TOKEN)
    if body:
        r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print("  [PASS] " + name)
        passed += 1
    else:
        print("  [FAIL] " + name + " " + detail)
        failed += 1


print("=" * 60)
print("ProductPulse UAT (TC-001 ~ TC-009)")
print("=" * 60)

# TC-001
print("\n--- TC-001: Selection list ---")
s, r = req("GET", "/products/?sort_by=score&sort_order=desc&page=1&page_size=5")
check("list returns", s == 200 and r.get("code") == 0, str(r)[:80])
items = r.get("data", {}).get("items", []) if isinstance(r.get("data"), dict) else []
check("has products", len(items) > 0, "empty")
if items:
    check("sorted by score desc", all(
        (items[i].get("comprehensive_score") or 0) >= (items[i + 1].get("comprehensive_score") or 0)
        for i in range(len(items) - 1)
    ))

# TC-002
print("\n--- TC-002: Filter boundary ---")
s, r = req("GET", "/products/?min_score=100")
check("high score filter ok", r.get("code") == 0)
s, r = req("GET", "/products/?category=3D%20printer%20filament")
check("category filter ok", r.get("code") == 0)
data_items = r.get("data", {}).get("items", []) if isinstance(r.get("data"), dict) else []
wrong = [i for i in data_items if i.get("category") != "3D printer filament"]
check("category filter correct", len(wrong) == 0, str(len(wrong)) + " wrong")

# TC-003
print("\n--- TC-003: Risk rules ---")
s, r = req("GET", "/config/risk-rules")
rules = r.get("data", {}).get("items", []) if isinstance(r.get("data"), dict) else []
check("preset rules exist", len(rules) >= 2)
check("has danger level", any(x["risk_level"] == "danger" for x in rules))

# TC-004
print("\n--- TC-004: Dashboard ---")
s, r = req("GET", "/dashboard/overview")
d = r.get("data", {}) or {}
check("KPI cards present", all(k in d for k in ["alerts_count", "pending_sku_count", "top_score"]))
check("alerts >= 0", isinstance(d.get("alerts_count"), int) and d["alerts_count"] >= 0)

# TC-005
print("\n--- TC-005: AI report ---")
s, r = req("GET", "/reports/daily")
check("report endpoint ok", r.get("code") == 0)
if r.get("data"):
    check("report has content", bool(r["data"].get("recommendations")))
    check("four modules", all(r["data"].get(k) for k in ["recommendations", "trend_analysis", "risk_alerts", "action_suggestions"]))
    print("    model: " + str(r["data"].get("model_used")) + " | ms: " + str(r["data"].get("generation_time_ms")))
else:
    print("    no report today (POST /reports/generate to create)")

# TC-006
print("\n--- TC-006: Config hot update ---")
s, r = req("PUT", "/config/thresholds", {"monthly_sales_min": 8888})
check("threshold update ok", r.get("code") == 0)
check("new value applied", r.get("data", {}).get("monthly_sales_min") == 8888)
req("PUT", "/config/thresholds", {"monthly_sales_min": 5000})

# TC-007
print("\n--- TC-007: Price alerts ---")
s, r = req("GET", "/price/alerts")
check("alerts endpoint ok", r.get("code") == 0)
check("alerts is list", isinstance(r.get("data", {}).get("items"), list))

# TC-008
print("\n--- TC-008: Performance ---")
latencies = []
for _ in range(5):
    t0 = time.time()
    req("GET", "/products/?page=1&page_size=20")
    latencies.append((time.time() - t0) * 1000)
avg = sum(latencies) / len(latencies)
check("avg response " + str(round(avg)) + "ms < 800ms", avg < 800, str(round(avg)) + "ms")

# TC-009
print("\n--- TC-009: Error handling ---")
bad_r = urllib.request.Request(BASE + "/products/")
bad_r.add_header("Authorization", "Bearer invalid")
try:
    resp = urllib.request.urlopen(bad_r)
    body = json.loads(resp.read())
except urllib.error.HTTPError as e:
    body = json.loads(e.read())
check("bad token returns 4001", body.get("code") == 4001)
check("unified response format", "message" in body and "timestamp" in body)

print("\n" + "=" * 60)
print("UAT Result: " + str(passed) + " passed, " + str(failed) + " failed")
if failed == 0:
    print(">>> ALL PASSED - UAT ACCEPTED <<<")
else:
    print(">>> " + str(failed) + " case(s) FAILED <<<")
print("=" * 60)