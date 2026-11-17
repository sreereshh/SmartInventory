"""
Order business logic. Everything that touches stock runs in one database
transaction: if any line fails, the whole order is rolled back.
"""
import uuid
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from inventory.models import StockTransaction
from inventory.services import StockError, apply_stock
from products.models import Product

from .models import Order, OrderItem


class OrderError(Exception):
    """Validation problem while creating/updating an order. `.errors` is a list of messages."""

    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(self.errors))


ALLOWED_TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.COMPLETED, Order.Status.CANCELLED},
    Order.Status.COMPLETED: set(),
    Order.Status.CANCELLED: set(),
}


def _merge_items(items):
    """Validate raw line items and merge duplicate products. Returns {product_id: quantity}."""
    merged = {}
    for item in items or []:
        try:
            product_id = int(item["product"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise OrderError("Every line needs a valid product and a whole-number quantity.")
        if quantity < 1:
            raise OrderError("Quantity must be at least 1 for every product.")
        merged[product_id] = merged.get(product_id, 0) + quantity
    if not merged:
        raise OrderError("Add at least one product to the order.")
    return merged


def create_order(*, customer, items, user=None, notes=""):
    """
    Create an order and reduce stock atomically.

    items: iterable of {"product": <id>, "quantity": <int>}
    Returns (order, low_stock_products). Raises OrderError on any problem
    (nothing is saved in that case).
    """
    merged = _merge_items(items)

    with transaction.atomic():
        products = {p.pk: p for p in Product.objects.filter(pk__in=merged.keys())}

        errors = []
        for product_id, quantity in merged.items():
            product = products.get(product_id)
            if product is None:
                errors.append(f"Product #{product_id} does not exist.")
            elif quantity > product.quantity:
                errors.append(
                    f"Insufficient stock for {product.name} ({product.code}): "
                    f"available {product.quantity}, requested {quantity}."
                )
        if errors:
            raise OrderError(errors)

        order = Order.objects.create(
            order_number=uuid.uuid4().hex[:16],  # replaced below once the id is known
            customer=customer,
            notes=notes or "",
            created_by=user,
            status=Order.Status.PENDING,
        )
        order.order_number = f"ORD-{order.pk:05d}"
        order.save(update_fields=["order_number"])

        total = Decimal("0.00")
        for product_id in sorted(merged):
            product, quantity = products[product_id], merged[product_id]
            try:
                apply_stock(
                    product_id=product_id,
                    quantity=quantity,
                    transaction_type=StockTransaction.Type.OUT,
                    reason=StockTransaction.Reason.SALE,
                    user=user,
                    order=order,
                    note=f"Sold on order {order.order_number}",
                )
            except StockError as exc:  # e.g. someone else bought the stock a moment ago
                raise OrderError(str(exc))
            subtotal = product.selling_price * quantity
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=product.selling_price,
                unit_cost=product.purchase_price,
                subtotal=subtotal,
            )
            total += subtotal

        order.total_amount = total
        order.save(update_fields=["total_amount", "updated_at"])

    low_stock = list(Product.objects.filter(pk__in=merged.keys(), quantity__lte=F("min_stock_level")))
    return order, low_stock


def change_status(order_id, new_status, user=None):
    """Move an order to a new status. Cancelling restores the stock."""
    if new_status not in Order.Status.values:
        raise OrderError("Invalid status.")

    with transaction.atomic():
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            raise OrderError("Order does not exist.")

        if new_status not in ALLOWED_TRANSITIONS[order.status]:
            raise OrderError(
                f"An order that is {order.get_status_display().lower()} cannot be changed to "
                f"{Order.Status(new_status).label.lower()}."
            )

        # Conditional update guards against two people changing the same order at once.
        changed = Order.objects.filter(pk=order.pk, status=order.status).update(
            status=new_status, updated_at=timezone.now()
        )
        if not changed:
            raise OrderError("This order was just changed by someone else. Please reload and try again.")

        if new_status == Order.Status.CANCELLED:
            for item in order.items.all():
                apply_stock(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    transaction_type=StockTransaction.Type.IN,
                    reason=StockTransaction.Reason.ORDER_CANCEL,
                    user=user,
                    order=order,
                    note=f"Order {order.order_number} cancelled – stock restored",
                )
    order.refresh_from_db()
    return order
