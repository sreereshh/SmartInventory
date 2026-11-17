from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.report_index, name="index"),
    path("daily/", views.daily_sales, name="daily"),
    path("monthly/", views.monthly_sales, name="monthly"),
    path("total-sales/", views.total_sales, name="total"),
    path("inventory/", views.inventory_report, name="inventory"),
    path("low-stock/", views.low_stock, name="low_stock"),
    path("orders/", views.order_report, name="orders"),
]
