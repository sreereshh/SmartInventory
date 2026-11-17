from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField("Product code", max_length=30, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    # Changed ONLY through inventory.services.apply_stock so every change is audited.
    quantity = models.PositiveIntegerField("Available quantity", default=0)
    min_stock_level = models.PositiveIntegerField("Minimum stock level", default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(purchase_price__gte=0), name="product_purchase_price_gte_0"),
            models.CheckConstraint(condition=Q(selling_price__gte=0), name="product_selling_price_gte_0"),
        ]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["code"])]

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        super().save(*args, **kwargs)

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity == 0

    @property
    def is_low_stock(self) -> bool:
        """True when quantity is at or below the minimum stock level (includes out of stock)."""
        return self.quantity <= self.min_stock_level

    @property
    def stock_status(self) -> str:
        if self.quantity == 0:
            return "out"
        if self.quantity <= self.min_stock_level:
            return "low"
        return "ok"

    @property
    def stock_value(self) -> Decimal:
        return self.purchase_price * self.quantity

    def __str__(self):
        return f"{self.name} ({self.code})"


def low_stock_queryset():
    return Product.objects.filter(quantity__lte=F("min_stock_level"))
