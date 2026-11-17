from django.conf import settings
from django.db.models import F

from products.models import Product


def global_context(request):
    """Values available in every template (currency, nav state, low-stock bell)."""
    context = {"CURRENCY": settings.CURRENCY_SYMBOL, "APP_NAME": "SmartInventory"}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        low_qs = Product.objects.filter(quantity__lte=F("min_stock_level"))
        context["low_stock_count"] = low_qs.count()
        context["low_stock_preview"] = list(low_qs.order_by("quantity", "name")[:5])
        match = getattr(request, "resolver_match", None)
        context["nav"] = (match.app_name or match.url_name) if match else ""
        context["nav_name"] = match.url_name if match and match.url_name else ""
    return context
