from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q
from django.shortcuts import redirect, render

from core.utils import paginate, parse_date
from products.models import Category, Product

from .forms import StockMovementForm
from .models import StockTransaction
from .services import StockError, apply_stock


@login_required
def stock_list(request):
    """Current stock for every product with low-stock highlighting."""
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    products = Product.objects.select_related("category")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if category.isdigit():
        products = products.filter(category_id=int(category))
    if status == "low":
        products = products.filter(quantity__lte=F("min_stock_level"), quantity__gt=0)
    elif status == "out":
        products = products.filter(quantity=0)
    elif status == "ok":
        products = products.filter(quantity__gt=F("min_stock_level"))

    page, qs = paginate(request, products, 12)
    return render(
        request,
        "inventory/stock_list.html",
        {"page": page, "qs": qs, "q": q, "category": category, "status": status,
         "categories": Category.objects.all()},
    )


def _movement_view(request, transaction_type):
    is_in = transaction_type == StockTransaction.Type.IN
    initial = {}
    if request.GET.get("product", "").isdigit():
        initial["product"] = int(request.GET["product"])

    form = StockMovementForm(request.POST or None, transaction_type=transaction_type, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            txn = apply_stock(
                product_id=form.cleaned_data["product"].pk,
                quantity=form.cleaned_data["quantity"],
                transaction_type=transaction_type,
                reason=form.cleaned_data["reason"],
                note=form.cleaned_data["note"],
                user=request.user,
            )
        except StockError as exc:
            form.add_error(None, str(exc))
        else:
            product = txn.product
            verb = "added to" if is_in else "removed from"
            messages.success(
                request,
                f"{txn.quantity} unit(s) {verb} {product.name}. New stock: {txn.quantity_after}.",
            )
            if product.is_low_stock:
                messages.warning(
                    request,
                    f"Low stock alert: {product.name} has {product.quantity} left "
                    f"(minimum level {product.min_stock_level}).",
                )
            return redirect("inventory:stock_list")

    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": "Stock In (receive stock)" if is_in else "Stock Out (remove stock)",
            "cancel_url": "inventory:stock_list",
            "submit_label": "Record stock in" if is_in else "Record stock out",
            "icon": "bi-box-arrow-in-down" if is_in else "bi-box-arrow-up",
            "info": "Stock can never go below zero. Sales are removed automatically when you create orders."
            if not is_in else "Increases the available quantity and logs a stock transaction.",
        },
    )


@login_required
def stock_in(request):
    return _movement_view(request, StockTransaction.Type.IN)


@login_required
def stock_out(request):
    return _movement_view(request, StockTransaction.Type.OUT)


@login_required
def stock_history(request):
    q = request.GET.get("q", "").strip()
    ttype = request.GET.get("type", "")
    reason = request.GET.get("reason", "")
    date_from = parse_date(request.GET.get("date_from"))
    date_to = parse_date(request.GET.get("date_to"))

    txns = StockTransaction.objects.select_related("product", "created_by", "order")
    if q:
        txns = txns.filter(Q(product__name__icontains=q) | Q(product__code__icontains=q) | Q(note__icontains=q))
    if ttype in StockTransaction.Type.values:
        txns = txns.filter(transaction_type=ttype)
    if reason in StockTransaction.Reason.values:
        txns = txns.filter(reason=reason)
    if date_from:
        txns = txns.filter(created_at__date__gte=date_from)
    if date_to:
        txns = txns.filter(created_at__date__lte=date_to)

    page, qs = paginate(request, txns, 15)
    return render(
        request,
        "inventory/stock_history.html",
        {
            "page": page, "qs": qs, "q": q, "type": ttype, "reason": reason,
            "date_from": request.GET.get("date_from", ""), "date_to": request.GET.get("date_to", ""),
            "reasons": StockTransaction.Reason.choices,
        },
    )
