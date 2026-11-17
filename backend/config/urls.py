from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", core_views.dashboard, name="dashboard"),
    path("", include("accounts.urls")),
    path("products/", include("products.urls")),
    path("inventory/", include("inventory.urls")),
    path("customers/", include("customers.urls")),
    path("orders/", include("orders.urls")),
    path("reports/", include("reports.urls")),
    path("api/", include("api.urls")),
]
