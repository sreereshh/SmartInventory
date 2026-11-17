from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import paginate, parse_date
from customers.models import Customer
from products.models import Product

from .models import Order
from .services import OrderError, change_status, create_order


@login_required
def order_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    date_from = parse_date(request.GET.get("date_from"))
    date_to = parse_date(request.GET.get("date_to"))

    orders = Order.objects.select_related("customer", "created_by").annotate(
        item_count=Count("items"), units=Sum("items__quantity")
    )
    if q:
        orders = orders.filter(Q(order_number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__phone__icontains=q))
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    page, qs = paginate(request, orders.order_by("-created_at", "-id"), 10)
    return render(
        request,
        "orders/order_list.html",
        {
            "page": page, "qs": qs, "q": q, "status": status,
            "date_from": request.GET.get("date_from", ""), "date_to": request.GET.get("date_to", ""),
            "statuses": Order.Status.choices,
        },
    )


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "created_by").prefetch_related("items__product"), pk=pk
    )
    return render(
        request,
        "orders/order_detail.html",
        {"order": order, "stock_txns": order.stock_transactions.select_related("product", "created_by")},
    )


@login_required
def order_create(request):
    customers = Customer.objects.order_by("name")
    products = Product.objects.order_by("name")
    selected_customer = request.GET.get("customer", "")
    notes = ""
    rows = []

    if request.method == "POST":
        selected_customer = request.POST.get("customer", "")
        notes = request.POST.get("notes", "").strip()
        product_ids = request.POST.getlist("product")
        quantities = request.POST.getlist("quantity")
        rows = [{"product": p, "quantity": q} for p, q in zip(product_ids, quantities) if p]

        customer = Customer.objects.filter(pk=selected_customer).first() if selected_customer.isdigit() else None
        if customer is None:
            messages.error(request, "Please select a customer.")
        else:
            try:
                order, low_stock = create_order(customer=customer, items=rows, user=request.user, notes=notes)
            except OrderError as exc:
                for error in exc.errors:
                    messages.error(request, error)
            else:
                messages.success(
                    request,
                    f"Order {order.order_number} created. Total: {order.total_amount}. Stock updated automatically.",
                )
                for product in low_stock:
                    messages.warning(
                        request,
                        f"Low stock alert: {product.name} now has {product.quantity} "
                        f"(minimum level {product.min_stock_level}).",
                    )
                return redirect("orders:detail", pk=order.pk)

    product_data = [
        {"id": p.pk, "name": p.name, "code": p.code, "price": float(p.selling_price), "stock": p.quantity}
        for p in products
    ]
    return render(
        request,
        "orders/order_form.html",
        {
            "customers": customers,
            "selected_customer": str(selected_customer),
            "notes": notes,
            "product_data": product_data,
            "rows": rows,
        },
    )


@login_required
@require_POST
def order_status(request, pk):
    new_status = request.POST.get("status", "")
    try:
        order = change_status(pk, new_status, user=request.user)
    except OrderError as exc:
        for error in exc.errors:
            messages.error(request, error)
    else:
        if order.status == Order.Status.CANCELLED:
            messages.success(request, f"Order {order.order_number} cancelled and stock restored.")
        else:
            messages.success(request, f"Order {order.order_number} marked as {order.get_status_display()}.")
    return redirect("orders:detail", pk=pk)
