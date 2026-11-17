from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("products", views.ProductViewSet, basename="product")
router.register("customers", views.CustomerViewSet, basename="customer")
router.register("orders", views.OrderViewSet, basename="order")

urlpatterns = [
    # Documentation (Swagger UI / ReDoc / raw OpenAPI schema)
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Authentication
    path("auth/login/", views.LoginView.as_view(), name="api-login"),
    path("auth/register/", views.RegisterView.as_view(), name="api-register"),
    path("auth/logout/", views.LogoutView.as_view(), name="api-logout"),
    path("auth/me/", views.MeView.as_view(), name="api-me"),
    # Inventory
    path("inventory/stock/", views.StockLevelView.as_view(), name="api-stock"),
    path("inventory/low-stock/", views.LowStockView.as_view(), name="api-low-stock"),
    path("inventory/transactions/", views.StockTransactionListView.as_view(), name="api-transactions"),
    path("inventory/stock-in/", views.StockInView.as_view(), name="api-stock-in"),
    path("inventory/stock-out/", views.StockOutView.as_view(), name="api-stock-out"),
    # Dashboard & reports
    path("dashboard/", views.DashboardView.as_view(), name="api-dashboard"),
    path("reports/daily/", views.DailyReportView.as_view(), name="api-report-daily"),
    path("reports/monthly/", views.MonthlyReportView.as_view(), name="api-report-monthly"),
    path("reports/total-sales/", views.TotalSalesReportView.as_view(), name="api-report-total"),
    path("reports/inventory/", views.InventoryReportView.as_view(), name="api-report-inventory"),
    path("reports/low-stock/", views.LowStockReportView.as_view(), name="api-report-low-stock"),
    path("reports/orders/", views.OrderReportView.as_view(), name="api-report-orders"),
    # CRUD resources
    path("", include(router.urls)),
]
