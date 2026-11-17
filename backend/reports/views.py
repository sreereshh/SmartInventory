from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from core.utils import parse_date, parse_month
from customers.models import Customer
from orders.models import Order
from products.models import Category

from . import services


@login_required
def report_index(request):
    return render(request, "reports/index.html")


@login_required
def daily_sales(request):
    day = parse_date(request.GET.get("date"), timezone.localdate())
    return render(request, "reports/daily.html", {"report": services.daily_report(day), "day": day})


@login_required
def monthly_sales(request):
    today = timezone.localdate()
    year, month = parse_month(request.GET.get("month"), (today.year, today.month))
    return render(
        request,
        "reports/monthly.html",
        {"report": services.monthly_report(year, month), "month_value": f"{year:04d}-{month:02d}",
         "month_label": f"{year}-{month:02d}"},
    )


@login_required
def total_sales(request):
    return render(request, "reports/total.html", {"report": services.total_sales_report()})


@login_required
def inventory_report(request):
    category = request.GET.get("category", "")
    report = services.inventory_report(int(category) if category.isdigit() else None)
    return render(
        request,
        "reports/inventory.html",
        {"report": report, "category": category, "categories": Category.objects.all()},
    )


@login_required
def low_stock(request):
    return render(request, "reports/low_stock.html", {"report": services.low_stock_report()})


@login_required
def order_report(request):
    date_from = parse_date(request.GET.get("date_from"))
    date_to = parse_date(request.GET.get("date_to"))
    status = request.GET.get("status", "")
    customer = request.GET.get("customer", "")
    report = services.order_report(
        date_from, date_to, status, int(customer) if customer.isdigit() else None
    )
    return render(
        request,
        "reports/orders.html",
        {
            "report": report,
            "date_from": request.GET.get("date_from", ""),
            "date_to": request.GET.get("date_to", ""),
            "status": status,
            "customer": customer,
            "statuses": Order.Status.choices,
            "customers": Customer.objects.all(),
        },
    )
