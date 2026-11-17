"""
Reporting queries shared by the web UI and the REST API.

"Sales" always means orders that are NOT cancelled. Every figure comes from the database.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from customers.models import Customer
from orders.models import Order, OrderItem
from products.models import Category, Product

MONEY = DecimalField(max_digits=16, decimal_places=2)
ZERO = Value(Decimal("0.00"), output_field=MONEY)


def _money_sum(expression):
    return Coalesce(Sum(expression), ZERO, output_field=MONEY)


def _profit_expression():
    return ExpressionWrapper((F("unit_price") - F("unit_cost")) * F("quantity"), output_field=MONEY)


def sellable(orders):
    """Orders that count towards sales (everything except cancelled)."""
    return orders.exclude(status=Order.Status.CANCELLED)


def summarize_orders(orders):
    valid = sellable(orders)
    base = valid.aggregate(order_count=Count("id"), total_sales=_money_sum("total_amount"))
    items = OrderItem.objects.filter(order__in=valid.values("pk")).aggregate(
        units_sold=Coalesce(Sum("quantity"), 0),
        gross_profit=_money_sum(_profit_expression()),
    )
    count = base["order_count"]
    return {
        "order_count": count,
        "total_sales": base["total_sales"],
        "units_sold": items["units_sold"],
        "gross_profit": items["gross_profit"],
        "average_order_value": (base["total_sales"] / count) if count else Decimal("0.00"),
    }


def product_breakdown(orders, limit=None):
    rows = (
        OrderItem.objects.filter(order__in=sellable(orders).values("pk"))
        .values("product_id", "product__name", "product__code")
        .annotate(units=Sum("quantity"), revenue=_money_sum("subtotal"))
        .order_by("-revenue", "product__name")
    )
    if limit:
        rows = rows[:limit]
    return [
        {
            "product_id": r["product_id"],
            "name": r["product__name"],
            "code": r["product__code"],
            "units": r["units"],
            "revenue": r["revenue"],
        }
        for r in rows
    ]


def order_rows(orders):
    rows = orders.select_related("customer").annotate(units=Coalesce(Sum("items__quantity"), 0))
    return [
        {
            "id": o.pk,
            "order_number": o.order_number,
            "customer": o.customer.name,
            "status": o.status,
            "status_display": o.get_status_display(),
            "total_amount": o.total_amount,
            "units": o.units,
            "created_at": o.created_at,
        }
        for o in rows
    ]


# ------------------------------------------------------------------ reports
def daily_report(day):
    orders = Order.objects.filter(created_at__date=day)
    return {
        "date": day,
        "summary": summarize_orders(orders),
        "products": product_breakdown(orders),
        "orders": order_rows(orders),
    }


def monthly_report(year, month):
    orders = Order.objects.filter(created_at__year=year, created_at__month=month)
    per_day = (
        sellable(orders)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(orders=Count("id"), total=_money_sum("total_amount"))
        .order_by("day")
    )
    return {
        "year": year,
        "month": month,
        "summary": summarize_orders(orders),
        "daily": [{"date": r["day"], "orders": r["orders"], "total": r["total"]} for r in per_day],
        "products": product_breakdown(orders, limit=10),
    }


def total_sales_report():
    orders = Order.objects.all()
    per_month = (
        sellable(orders)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(orders=Count("id"), total=_money_sum("total_amount"))
        .order_by("-month")
    )
    top_customers = (
        sellable(orders)
        .values("customer_id", "customer__name")
        .annotate(orders=Count("id"), total=_money_sum("total_amount"))
        .order_by("-total")[:10]
    )
    return {
        "summary": summarize_orders(orders),
        "monthly": [{"month": r["month"], "orders": r["orders"], "total": r["total"]} for r in per_month],
        "products": product_breakdown(orders, limit=10),
        "customers": [
            {"customer_id": r["customer_id"], "name": r["customer__name"], "orders": r["orders"], "total": r["total"]}
            for r in top_customers
        ],
        "cancelled_orders": orders.filter(status=Order.Status.CANCELLED).count(),
    }


def inventory_report(category_id=None):
    products = Product.objects.select_related("category").order_by("category__name", "name")
    if category_id:
        products = products.filter(category_id=category_id)
    rows, cost_total, retail_total, units = [], Decimal("0.00"), Decimal("0.00"), 0
    low = out = 0
    for p in products:
        cost, retail = p.purchase_price * p.quantity, p.selling_price * p.quantity
        cost_total += cost
        retail_total += retail
        units += p.quantity
        low += 1 if p.stock_status == "low" else 0
        out += 1 if p.stock_status == "out" else 0
        rows.append(
            {
                "id": p.pk, "name": p.name, "code": p.code, "category": p.category.name,
                "quantity": p.quantity, "min_stock_level": p.min_stock_level,
                "purchase_price": p.purchase_price, "selling_price": p.selling_price,
                "cost_value": cost, "retail_value": retail, "stock_status": p.stock_status,
            }
        )
    return {
        "summary": {
            "product_count": len(rows), "total_units": units, "cost_value": cost_total,
            "retail_value": retail_total, "low_stock_count": low, "out_of_stock_count": out,
        },
        "products": rows,
    }


def low_stock_report():
    products = Product.objects.select_related("category").filter(quantity__lte=F("min_stock_level")).order_by("quantity", "name")
    rows = [
        {
            "id": p.pk, "name": p.name, "code": p.code, "category": p.category.name,
            "quantity": p.quantity, "min_stock_level": p.min_stock_level,
            "shortfall": p.min_stock_level - p.quantity,
            # Suggested restock = enough to reach twice the minimum level.
            "suggested_restock": max(p.min_stock_level * 2 - p.quantity, 0),
            "stock_status": p.stock_status,
        }
        for p in products
    ]
    return {
        "summary": {
            "low_stock_count": sum(1 for r in rows if r["stock_status"] == "low"),
            "out_of_stock_count": sum(1 for r in rows if r["stock_status"] == "out"),
        },
        "products": rows,
    }


def order_report(date_from=None, date_to=None, status=None, customer_id=None):
    orders = Order.objects.all()
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    by_status = {
        label: orders.filter(status=value).count() for value, label in Order.Status.choices
    }
    return {
        "summary": summarize_orders(orders),
        "by_status": by_status,
        "orders": order_rows(orders),
    }


# ---------------------------------------------------------------- dashboard
def dashboard_data():
    today = timezone.localdate()
    orders = Order.objects.all()
    valid = sellable(orders)

    totals = summarize_orders(orders)
    today_summary = summarize_orders(orders.filter(created_at__date=today))
    month_summary = summarize_orders(orders.filter(created_at__year=today.year, created_at__month=today.month))

    # Last 7 days (including today), zero-filled.
    start = today - timedelta(days=6)
    per_day = {
        r["day"]: r["total"]
        for r in sellable(orders.filter(created_at__date__gte=start))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=_money_sum("total_amount"))
    }
    last_7_days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        last_7_days.append({"date": day, "label": day.strftime("%d %b"), "total": per_day.get(day, Decimal("0.00"))})

    status_counts = {
        value: orders.filter(status=value).count() for value, _label in Order.Status.choices
    }

    inventory = Product.objects.aggregate(
        total_units=Coalesce(Sum("quantity"), 0),
        cost_value=_money_sum(ExpressionWrapper(F("quantity") * F("purchase_price"), output_field=MONEY)),
        retail_value=_money_sum(ExpressionWrapper(F("quantity") * F("selling_price"), output_field=MONEY)),
    )
    low_qs = Product.objects.filter(quantity__lte=F("min_stock_level"))
    stock_by_category = [
        {
            "category": c.name,
            "units": c.units,
            "value": c.value,
        }
        for c in Category.objects.annotate(
            units=Coalesce(Sum("products__quantity"), 0),
            value=_money_sum(ExpressionWrapper(F("products__quantity") * F("products__purchase_price"), output_field=MONEY)),
        ).order_by("name")
    ]

    recent_orders = [
        {
            "id": o.pk, "order_number": o.order_number, "customer": o.customer.name, "status": o.status,
            "status_display": o.get_status_display(), "total_amount": o.total_amount, "created_at": o.created_at,
        }
        for o in orders.select_related("customer")[:8]
    ]
    low_stock_products = [
        {
            "id": p.pk, "name": p.name, "code": p.code, "quantity": p.quantity,
            "min_stock_level": p.min_stock_level, "stock_status": p.stock_status,
        }
        for p in low_qs.order_by("quantity", "name")[:8]
    ]

    return {
        "total_products": Product.objects.count(),
        "total_customers": Customer.objects.count(),
        "total_orders": orders.count(),
        "total_sales": totals["total_sales"],
        "low_stock_count": low_qs.count(),
        "out_of_stock_count": Product.objects.filter(quantity=0).count(),
        "sales": {
            "today": today_summary["total_sales"],
            "today_orders": today_summary["order_count"],
            "this_month": month_summary["total_sales"],
            "this_month_orders": month_summary["order_count"],
            "gross_profit": totals["gross_profit"],
            "average_order_value": totals["average_order_value"],
            "units_sold": totals["units_sold"],
            "last_7_days": last_7_days,
            "orders_by_status": status_counts,
            "top_products": product_breakdown(orders, limit=5),
        },
        "inventory": {
            "total_units": inventory["total_units"],
            "cost_value": inventory["cost_value"],
            "retail_value": inventory["retail_value"],
            "stock_by_category": stock_by_category,
        },
        "recent_orders": recent_orders,
        "low_stock_products": low_stock_products,
    }
