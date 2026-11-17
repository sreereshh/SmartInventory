"""Usage: start the server (python manage.py runserver), then: python live_tests/api_and_web_live_test.py
Use a freshly seeded database; the script creates/changes data.
Live end-to-end check against the running server: web UI (session + CSRF) and REST API (token)."""
import json, re, sys, urllib.request, urllib.parse, http.cookiejar
BASE = "http://127.0.0.1:8000"
ok = fail = 0
def check(name, cond, extra=""):
    global ok, fail
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    ok += bool(cond); fail += (not cond)

# ---------------- web UI
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def get(path):
    return op.open(BASE + path)
def csrf():
    return next(c.value for c in jar if c.name == "csrftoken")
def post(path, data):
    get(path) if not any(c.name == "csrftoken" for c in jar) else None
    data = dict(data, csrfmiddlewaretoken=csrf())
    body = urllib.parse.urlencode(data, doseq=True).encode()
    req = urllib.request.Request(BASE + path, body, {"Referer": BASE + path})
    try:
        return op.open(req)
    except urllib.error.HTTPError as e:
        return e

r = get("/"); check("dashboard redirects anonymous to login", "/login/" in r.url)
get("/login/")
r = post("/login/", {"username": "admin", "password": "Admin@12345"}); check("admin login", r.url.rstrip("/") == BASE and "Dashboard" in r.read().decode())
html = get("/").read().decode()
check("dashboard shows DB totals", "16" in html and "26" in html)
for path in ["/products/", "/products/categories/", "/inventory/", "/inventory/history/", "/customers/", "/orders/", "/orders/new/",
             "/reports/", "/reports/daily/", "/reports/monthly/", "/reports/total-sales/", "/reports/inventory/",
             "/reports/low-stock/", "/reports/orders/", "/profile/", "/users/", "/api/docs/", "/api/redoc/", "/api/schema/"]:
    try: code = get(path).status
    except urllib.error.HTTPError as e: code = e.code
    check(f"GET {path}", code == 200, code)

r = post("/products/add/", {"name": "E2E Gadget", "code": "e2e-1", "category": 1, "purchase_price": "100", "selling_price": "150",
                            "quantity": "7", "min_stock_level": "5", "description": "e2e"})
check("add product", "E2E Gadget" in r.read().decode())
page = get("/products/?q=E2E").read().decode(); check("search product", "E2E Gadget" in page)
pid = int(re.search(r"/products/(\d+)/edit/", page).group(1))
r = post(f"/products/{pid}/edit/", {"name": "E2E Gadget 2", "code": "E2E-1", "category": 1, "purchase_price": "100", "selling_price": "160", "min_stock_level": "5", "description": ""})
check("edit product", "E2E Gadget 2" in r.read().decode())
r = post("/inventory/stock-out/", {"product": pid, "quantity": "50", "reason": "damage", "note": ""}); check("stock-out overdraw blocked", "Insufficient stock" in r.read().decode())
r = post("/inventory/stock-out/", {"product": pid, "quantity": "3", "reason": "damage", "note": ""}); t = r.read().decode(); check("stock-out ok + low-stock alert", "Low stock alert" in t, t[:0])
r = post("/inventory/stock-in/", {"product": pid, "quantity": "20", "reason": "purchase", "note": "e2e"}); check("stock-in ok", "New stock: 24" in r.read().decode())
r = post("/customers/add/", {"name": "E2E Customer", "phone": "9000000099", "email": "e2e@example.com", "address": "x"})
check("add customer", "E2E Customer" in r.read().decode())
cpage = get("/customers/?q=E2E").read().decode(); cid = int(re.search(r"/customers/(\d+)/edit/", cpage).group(1))
r = post("/orders/new/", {"customer": cid, "notes": "e2e order", "product": [pid], "quantity": ["4"]})
body = r.read().decode(); check("create order", "ORD-" in body and "e2e order" in body)
oid = int(re.search(r"/orders/(\d+)/", r.url).group(1))
stock = get(f"/products/{pid}/").read().decode(); check("stock reduced automatically (24 -> 20)", re.search(r">\s*20\s*<", stock) is not None)
r = post("/orders/new/", {"customer": cid, "product": [pid], "quantity": ["999"]}); check("order blocked when stock insufficient", "Insufficient stock" in r.read().decode())
r = post(f"/orders/{oid}/status/", {"status": "cancelled"}); check("cancel order restores stock", "stock restored" in r.read().decode())
r = post(f"/customers/{cid}/delete/", {}); check("customer with a (cancelled) order cannot be deleted", "Cannot delete" in r.read().decode())
r = post("/customers/add/", {"name": "E2E Temp", "phone": "9000000088", "email": "", "address": ""}); tmp = int(re.search(r"/customers/(\d+)/edit/", get("/customers/?q=E2E+Temp").read().decode()).group(1))
r = post(f"/customers/{tmp}/delete/", {}); check("customer without orders deleted", "deleted" in r.read().decode() and "No customers found" in get("/customers/?q=E2E+Temp").read().decode())
get("/logout/") if False else None
r = post("/logout/", {}); check("logout", "/login/" in r.url)
r = get("/"); check("dashboard protected after logout", "/login/" in r.url)

# staff RBAC
jar.clear(); get("/login/"); post("/login/", {"username": "staff", "password": "Staff@12345"})
try: code = get("/users/").status
except urllib.error.HTTPError as e: code = e.code
check("staff blocked from /users/ (403)", code == 403, code)
r = post(f"/products/{pid}/delete/", {}); check("staff cannot delete product (403)", r.code == 403 if hasattr(r, "code") else False)

# ---------------- REST API
def api(method, path, data=None, token=None):
    req = urllib.request.Request(BASE + path, json.dumps(data).encode() if data is not None else None, method=method,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Token {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req) as resp: return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")
s, d = api("POST", "/api/auth/login/", {"username": "admin", "password": "wrong"}); check("API bad login -> 401", s == 401)
s, d = api("POST", "/api/auth/login/", {"username": "staff", "password": "Staff@12345"}); check("API login -> token", s == 200 and d["token"])
tok = d["token"]
s, _ = api("GET", "/api/products/"); check("API without token -> 401", s == 401)
s, d = api("GET", "/api/products/?search=mouse", token=tok); check("API product search", s == 200 and d["count"] >= 1)
s, d = api("GET", "/api/dashboard/", token=tok); check("API dashboard", s == 200 and d["total_products"] >= 16, d.get("total_products"))
s, d = api("GET", "/api/inventory/low-stock/", token=tok); check("API low stock", s == 200 and d["count"] >= 1)
s, d = api("GET", "/api/customers/", token=tok); cust = d["results"][0]["id"]; check("API customers", s == 200)
s, d = api("GET", "/api/products/?status=ok", token=tok); prod = d["results"][0]
s, d = api("POST", "/api/orders/", {"customer": cust, "items": [{"product": prod["id"], "quantity": 2}]}, tok); check("API create order 201", s == 201 and d["order_number"].startswith("ORD-"), d)
s, d2 = api("GET", f"/api/products/{prod['id']}/", token=tok); check("API stock reduced", d2["quantity"] == prod["quantity"] - 2)
s, d = api("POST", "/api/orders/", {"customer": cust, "items": [{"product": prod["id"], "quantity": 99999}]}, tok); check("API insufficient stock -> 400", s == 400 and "Insufficient" in d["detail"])
s, d = api("DELETE", f"/api/products/{prod['id']}/", token=tok); check("API staff delete -> 403", s == 403)
for rp in ["daily", "monthly", "total-sales", "inventory", "low-stock", "orders"]:
    s, d = api("GET", f"/api/reports/{rp}/", token=tok); check(f"API report {rp}", s == 200)
s, d = api("POST", "/api/auth/logout/", token=tok); check("API logout", s == 200)
s, _ = api("GET", "/api/auth/me/", token=tok); check("API token revoked after logout", s == 401)
print(f"\n{ok} passed, {fail} failed"); sys.exit(1 if fail else 0)
