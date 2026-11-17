from django.contrib import admin

from .models import StockTransaction


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "transaction_type", "reason", "quantity", "quantity_after", "created_by")
    list_filter = ("transaction_type", "reason")
    search_fields = ("product__name", "product__code", "note")

    # Audit records are append-only.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
