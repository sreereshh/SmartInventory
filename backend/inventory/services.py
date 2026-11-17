"""
Stock service layer – the ONLY place that changes Product.quantity.

* Every change is atomic and recorded as a StockTransaction.
* Stock-out uses a conditional UPDATE (quantity >= requested) so stock can
  never go negative, even with concurrent requests.
"""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from products.models import Product

from .models import StockTransaction


class StockError(ValueError):
    """Raised when a stock movement is invalid (e.g. insufficient stock)."""


@transaction.atomic
def apply_stock(*, product_id, quantity, transaction_type, reason, user=None, note="", order=None):
    """Increase or decrease a product's stock and log a StockTransaction."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise StockError("Quantity must be a whole number greater than zero.")
    if transaction_type not in StockTransaction.Type.values:
        raise StockError("Invalid transaction type.")

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        raise StockError("Product does not exist.")

    now = timezone.now()
    if transaction_type == StockTransaction.Type.OUT:
        updated = Product.objects.filter(pk=product_id, quantity__gte=quantity).update(
            quantity=F("quantity") - quantity, updated_at=now
        )
        if not updated:
            raise StockError(
                f"Insufficient stock for {product.name} ({product.code}): "
                f"available {product.quantity}, requested {quantity}."
            )
    else:
        Product.objects.filter(pk=product_id).update(quantity=F("quantity") + quantity, updated_at=now)

    product.refresh_from_db()
    if transaction_type == StockTransaction.Type.OUT:
        before = product.quantity + quantity
    else:
        before = product.quantity - quantity

    txn = StockTransaction.objects.create(
        product=product,
        transaction_type=transaction_type,
        reason=reason,
        quantity=quantity,
        quantity_before=before,
        quantity_after=product.quantity,
        order=order,
        note=(note or "")[:255],
        created_by=user,
    )
    return txn


@transaction.atomic
def create_product_with_opening_stock(product, quantity=0, user=None):
    """Save a new Product; if it starts with stock, log an 'opening stock' transaction."""
    product.quantity = 0
    product.save()
    if quantity and quantity > 0:
        apply_stock(
            product_id=product.pk,
            quantity=int(quantity),
            transaction_type=StockTransaction.Type.IN,
            reason=StockTransaction.Reason.OPENING,
            user=user,
            note="Opening stock when product was created",
        )
        product.refresh_from_db()
    return product
