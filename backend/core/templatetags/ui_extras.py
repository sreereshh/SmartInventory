from django import template

register = template.Library()

ORDER_BADGES = {
    "pending": "warning",
    "confirmed": "info",
    "completed": "success",
    "cancelled": "danger",
}


@register.filter
def order_badge(status):
    """Bootstrap colour name for an order status."""
    return ORDER_BADGES.get(status, "secondary")


@register.filter
def stock_badge(status):
    return {"out": "danger", "low": "warning", "ok": "success"}.get(status, "secondary")


@register.filter
def stock_label(status):
    return {"out": "Out of stock", "low": "Low stock", "ok": "In stock"}.get(status, status)


@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except TypeError:
        return ""
