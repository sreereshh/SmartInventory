from django.conf import settings
from django.db import models
from django.db.models import Q


class StockTransaction(models.Model):
    """Immutable audit record of every stock movement."""

    class Type(models.TextChoices):
        IN = "IN", "Stock In"
        OUT = "OUT", "Stock Out"

    class Reason(models.TextChoices):
        OPENING = "opening", "Opening stock"
        PURCHASE = "purchase", "Purchase / restock"
        RETURN = "return", "Customer return"
        SALE = "sale", "Sale (order)"
        ORDER_CANCEL = "order_cancel", "Order cancelled"
        DAMAGE = "damage", "Damaged / expired"
        ADJUSTMENT = "adjustment", "Adjustment / correction"
        OTHER = "other", "Other"

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=3, choices=Type.choices)
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.OTHER)
    quantity = models.PositiveIntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_transactions"
    )
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="stocktx_quantity_gt_0"),
        ]

    def __str__(self):
        sign = "+" if self.transaction_type == self.Type.IN else "-"
        return f"{self.product.code} {sign}{self.quantity}"
