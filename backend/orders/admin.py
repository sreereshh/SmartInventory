from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price", "unit_cost", "subtotal")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("order_number", "customer__name")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "total_amount", "created_by")
