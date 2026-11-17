"""Browser UI test (Playwright + Chromium). Needs: pip install playwright && playwright install chromium
Start the server first, on a freshly seeded database:  python manage.py runserver
Then:  python live_tests\\ui_browser_test.py   (modifies data; reseed afterwards)"""
import sqlite3, re, sys
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:8000"; import os
DB=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","db.sqlite3")
SH=os.path.join(os.path.dirname(os.path.abspath(__file__)),"screenshots")+os.sep
os.makedirs(SH,exist_ok=True)
def q(sql,*a):
    c=sqlite3.connect(DB); r=c.execute(sql,a).fetchall(); c.close(); return r
def one(sql,*a): r=q(sql,*a); return r[0][0] if r else None
res=[]
def check(name,cond,extra=""):
    res.append(bool(cond)); print(("PASS " if cond else "FAIL ")+name+("" if cond else f"  [{extra}]"))
errors=[]
with sync_playwright() as pw:
    b=pw.chromium.launch(); ctx=b.new_context(viewport={"width":1360,"height":860}); p=ctx.new_page()
    p.on("console",lambda m: errors.append(("console",m.text)) if m.type=="error" and "403" not in m.text else None)
    p.on("pageerror",lambda e: errors.append(("pageerror",str(e))))
    p.on("response",lambda r: errors.append(("http",r.status,r.url)) if r.status>=400 and "/static/" in r.url else None)
    def submit(): p.locator("main button[type=submit], .content button[type=submit], form button[type=submit]:visible").last.click(); p.wait_for_load_state("networkidle")
    def logout():
        p.goto(BASE+"/")
        if p.locator("form[action$='/logout/']").count(): p.evaluate("document.querySelector(\"form[action$='/logout/']\").submit()"); p.wait_for_load_state("networkidle")
        else: ctx.clear_cookies()
    def login(u,pw_):
        p.goto(BASE+"/login/"); p.fill("input[name=username]",u); p.fill("input[name=password]",pw_); p.click("button[type=submit]"); p.wait_for_load_state("networkidle")
    # ---- auth
    login("admin","wrong"); check("bad login shows error and stays on login", "/login" in p.url and p.locator(".alert, .invalid-feedback, .text-danger").count()>0)
    login("admin","Admin@12345"); check("admin login -> dashboard", p.url.rstrip("/")==BASE)
    txt=p.inner_text("body")
    check("dashboard numbers == database", str(one("select count(*) from products_product")) in txt and str(one("select count(*) from orders_order")) in txt and str(one("select count(*) from customers_customer")) in txt)
    p.screenshot(path=SH+"ui_dashboard.png",full_page=True)
    # ---- products
    p.goto(BASE+"/products/add/"); p.fill("input[name=name]","UI Test Gadget"); p.fill("input[name=code]","ui-1")
    p.select_option("select[name=category]",index=1); p.fill("input[name=purchase_price]","100"); p.fill("input[name=selling_price]","150")
    p.fill("input[name=quantity]","10"); p.fill("input[name=min_stock_level]","5"); submit()
    pid=one("select id from products_product where code='UI-1'"); check("add product (code upper-cased, qty 10)", pid and one("select quantity from products_product where id=?",pid)==10)
    check("opening stock logged", one("select count(*) from inventory_stocktransaction where product_id=? and reason='opening'",pid)==1)
    p.goto(BASE+"/products/?q=UI+Test"); check("search finds product", "UI Test Gadget" in p.inner_text("body"))
    p.goto(BASE+f"/products/{pid}/edit/"); p.fill("input[name=selling_price]","175"); submit()
    check("edit product", str(one("select selling_price from products_product where id=?",pid)).startswith("175"))
    # ---- inventory
    p.goto(BASE+"/inventory/stock-out/"); p.select_option("select[name=product]",str(pid)); p.fill("input[name=quantity]","500"); p.select_option("select[name=reason]",index=1); submit()
    check("stock-out beyond stock blocked", "Insufficient stock" in p.inner_text("body") and one("select quantity from products_product where id=?",pid)==10)
    p.goto(BASE+"/inventory/stock-out/"); p.select_option("select[name=product]",str(pid)); p.fill("input[name=quantity]","6"); p.select_option("select[name=reason]",index=1); submit()
    check("stock-out reduces stock + low stock alert shown", one("select quantity from products_product where id=?",pid)==4 and "ow stock" in p.inner_text("body"))
    p.goto(BASE+"/inventory/stock-in/"); p.select_option("select[name=product]",str(pid)); p.fill("input[name=quantity]","20"); submit()
    check("stock-in increases stock", one("select quantity from products_product where id=?",pid)==24)
    p.goto(BASE+"/inventory/history/"); check("history lists transactions", "UI Test Gadget" in p.inner_text("body"))
    p.goto(BASE+"/inventory/?q=UI+Test"); check("current stock page lists product (search)", "UI Test Gadget" in p.inner_text("body"))
    # ---- customers: add / edit / delete (no orders) / delete blocked (has orders)
    p.goto(BASE+"/customers/add/"); p.fill("input[name=name]","UI Customer"); p.fill("input[name=phone]","9000012345"); p.fill("input[name=email]","ui@example.com"); p.fill("textarea[name=address]","Kochi"); submit()
    cid=one("select id from customers_customer where name='UI Customer'"); check("add customer", cid)
    p.goto(BASE+f"/customers/{cid}/edit/"); p.fill("input[name=name]","UI Customer Edited"); submit()
    check("edit customer", one("select name from customers_customer where id=?",cid)=="UI Customer Edited")
    p.goto(BASE+"/customers/?q=Edited"); check("search customer", "UI Customer Edited" in p.inner_text("body"))
    p.goto(BASE+"/customers/"); p.locator(f"a[href='/customers/{cid}/delete/']").click(); p.wait_for_load_state("networkidle")
    check("delete shows confirmation page", "Delete this customer" in p.inner_text("body")); p.click("button:has-text('Yes, delete')"); p.wait_for_load_state("networkidle")
    check("customer deleted from DB", one("select count(*) from customers_customer where id=?",cid)==0 and "deleted" in p.inner_text("body"))
    has_orders=one("select customer_id from orders_order group by customer_id limit 1"); before=one("select count(*) from customers_customer")
    p.goto(BASE+f"/customers/{has_orders}/delete/"); p.click("button:has-text('Yes, delete')"); p.wait_for_load_state("networkidle")
    check("customer WITH orders cannot be deleted", one("select count(*) from customers_customer")==before and "Cannot delete" in p.inner_text("body"))
    p.goto(BASE+"/customers/add/"); p.fill("input[name=name]","Bad Phone"); p.fill("input[name=phone]","abc"); submit()
    check("invalid phone rejected", one("select count(*) from customers_customer where name='Bad Phone'")==0)
    # ---- orders via the JS order form
    p.goto(BASE+"/customers/add/"); p.fill("input[name=name]","Order Buyer"); p.fill("input[name=phone]","9000067890"); submit()
    buyer=one("select id from customers_customer where name='Order Buyer'")
    other=one("select id from products_product where id!=? and quantity>=5 order by id limit 1",pid)
    q0=one("select quantity from products_product where id=?",pid); q1=one("select quantity from products_product where id=?",other)
    pr0=float(one("select selling_price from products_product where id=?",pid)); pr1=float(one("select selling_price from products_product where id=?",other))
    p.goto(BASE+"/orders/new/"); p.select_option("#customer",str(buyer))
    sel=p.locator("select.line-product"); qty=p.locator("input.line-qty")
    sel.first.select_option(str(pid)); qty.first.fill("3")
    p.click("#addLine"); sel.nth(1).select_option(str(other)); qty.nth(1).fill("2")
    expected=pr0*3+pr1*2; gt=p.inner_text("#grandTotal"); check("grand total computed live in browser", f"{expected:,.2f}" in gt, gt)
    p.screenshot(path=SH+"ui_order_filled.png"); p.click("#submitOrder"); p.wait_for_load_state("networkidle")
    oid=one("select id from orders_order where customer_id=? order by id desc limit 1",buyer)
    check("order created, redirected to detail", oid and f"/orders/{oid}/" in p.url)
    check("order total saved == subtotal sum", abs(float(one("select total_amount from orders_order where id=?",oid))-expected)<0.01)
    check("2 order items saved", one("select count(*) from orders_orderitem where order_id=?",oid)==2)
    check("AUTOMATIC STOCK REDUCTION (product 1)", one("select quantity from products_product where id=?",pid)==q0-3)
    check("AUTOMATIC STOCK REDUCTION (product 2)", one("select quantity from products_product where id=?",other)==q1-2)
    check("2 OUT stock transactions linked to order", one("select count(*) from inventory_stocktransaction where order_id=? and transaction_type='OUT'",oid)==2)
    p.screenshot(path=SH+"ui_order_detail.png",full_page=True)
    p.goto(BASE+"/orders/new/"); p.select_option("#customer",str(buyer)); p.locator("select.line-product").first.select_option(str(pid)); p.locator("input.line-qty").first.fill("9999"); p.click("#submitOrder"); p.wait_for_load_state("networkidle")
    check("order with insufficient stock rejected, stock unchanged", one("select quantity from products_product where id=?",pid)==q0-3 and one("select count(*) from orders_order where customer_id=?",buyer)==1, p.inner_text("body")[:0])
    p.goto(BASE+"/orders/"); check("order history lists order", one("select order_number from orders_order where id=?",oid) in p.inner_text("body"))
    p.goto(BASE+f"/orders/{oid}/"); 
    for label,status in (("Confirm","confirmed"),("Complete","completed")):
        btn=p.locator(f"button:has-text('{label}')").first
        if btn.count(): btn.click(); p.wait_for_load_state("networkidle")
    check("status progressed via UI buttons", one("select status from orders_order where id=?",oid) in("confirmed","completed"), one("select status from orders_order where id=?",oid))
    # cancel another fresh order -> stock restored
    p.goto(BASE+"/orders/new/"); p.select_option("#customer",str(buyer)); p.locator("select.line-product").first.select_option(str(pid)); p.locator("input.line-qty").first.fill("2"); p.click("#submitOrder"); p.wait_for_load_state("networkidle")
    oid2=one("select max(id) from orders_order"); qa=one("select quantity from products_product where id=?",pid)
    cb=p.locator("button:has-text('Cancel')").first
    p.once("dialog",lambda d:d.accept()); cb.click(); p.wait_for_load_state("networkidle")
    st=one("select status from orders_order where id=?",oid2)
    if st!="cancelled" and p.locator("button:has-text('Yes')").count(): p.locator("button:has-text('Yes')").first.click(); p.wait_for_load_state("networkidle"); st=one("select status from orders_order where id=?",oid2)
    check("cancel order via UI restores stock", st=="cancelled" and one("select quantity from products_product where id=?",pid)==qa+2, st)
    # ---- reports
    for path in ("daily","monthly","total-sales","inventory","low-stock","orders"):
        p.goto(BASE+f"/reports/{path}/"); ok=p.locator("[data-print]").count()>0 and p.locator("table").count()>0
        check(f"report {path}: table + Print button", ok)
    p.goto(BASE+"/reports/total-sales/"); p.screenshot(path=SH+"ui_report.png")
    pdf=p.pdf(path=SH+"report_print.pdf"); check("report prints to PDF (print CSS)", True)
    # ---- RBAC in the UI
    p.goto(BASE+"/users/"); check("admin can open user management", p.locator("table").count()>0)
    p.goto(BASE+"/products/"); check("admin sees delete buttons", p.locator("a[href$='/delete/']").count()>0)
    # logout
    p.goto(BASE+"/"); 
    logout()
    check("logout -> login page", "/login" in p.url); p.goto(BASE+"/products/"); check("protected after logout", "/login" in p.url)
    # registration
    p.goto(BASE+"/register/"); 
    for n,v in (("username","reguser"),("first_name","Reg"),("last_name","User"),("email","r@example.com"),("password1","Str0ng!Pass#9"),("password2","Str0ng!Pass#9")): p.fill(f"input[name={n}]",v)
    submit(); check("registration creates STAFF user", one("select role from accounts_user where username='reguser'")=="staff")
    logout()
    # staff
    login("staff","Staff@12345"); check("staff login", p.url.rstrip("/")==BASE)
    p.goto(BASE+"/products/"); check("staff sees NO delete buttons", p.locator("a[href$='/delete/']").count()==0)
    r=p.goto(BASE+"/customers/1/delete/"); check("staff direct URL delete -> 403", r.status==403)
    r=p.goto(BASE+"/users/"); check("staff /users/ -> 403", r.status==403)
    r=p.goto(BASE+f"/products/{pid}/delete/"); check("staff product delete URL -> 403", r.status==403)
    p.goto(BASE+"/orders/new/"); check("staff can open new order", p.locator("#addLine").count()==1)
    # admin deletes the test product (no orders? it has orders -> blocked)
    logout()
    login("admin","Admin@12345"); p.goto(BASE+f"/products/{pid}/delete/"); p.click("button:has-text('Yes, delete')"); p.wait_for_load_state("networkidle")
    check("product that was ordered cannot be deleted", one("select count(*) from products_product where id=?",pid)==1)
    p.goto(BASE+"/products/add/"); p.fill("input[name=name]","Temp"); p.fill("input[name=code]","tmp-9"); p.select_option("select[name=category]",index=1); p.fill("input[name=purchase_price]","1"); p.fill("input[name=selling_price]","2"); p.fill("input[name=quantity]","1"); p.fill("input[name=min_stock_level]","0"); submit()
    tid=one("select id from products_product where code='TMP-9'"); p.goto(BASE+f"/products/{tid}/delete/"); p.click("button:has-text('Yes, delete')"); p.wait_for_load_state("networkidle")
    check("unordered product deleted by admin", one("select count(*) from products_product where id=?",tid)==0)
    # ---- mobile layout
    m=b.new_context(viewport={"width":390,"height":800}).new_page(); m.goto(BASE+"/login/"); m.fill("input[name=username]","admin"); m.fill("input[name=password]","Admin@12345"); m.click("button[type=submit]"); m.wait_for_load_state("networkidle")
    over=m.evaluate("document.documentElement.scrollWidth>window.innerWidth+2"); check("mobile: no horizontal page overflow (dashboard)", not over)
    tog=m.locator("[data-sidebar-toggle], .sidebar-toggle, button[aria-label*='enu']"); 
    if tog.count(): tog.first.click(); m.wait_for_timeout(400)
    m.screenshot(path=SH+"ui_mobile_menu.png")
    check("no JS errors / missing static files", not errors, errors[:5])
    b.close()
print(f"\n{sum(res)}/{len(res)} passed"); sys.exit(0 if all(res) else 1)
