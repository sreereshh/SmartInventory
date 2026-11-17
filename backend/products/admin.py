from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "selling_price", "quantity", "min_stock_level")
    list_filter = ("category",)
    search_fields = ("name", "code")
    readonly_fields = ("quantity",)  # stock changes must go through Stock In / Stock Out
