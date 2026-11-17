from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required
from core.utils import paginate
from orders.models import Order

from .forms import CustomerForm
from .models import Customer


@login_required
def customer_list(request):
    q = request.GET.get("q", "").strip()
    customers = Customer.objects.annotate(order_count=Count("orders")).order_by("name", "id")
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q) | Q(address__icontains=q)
        )
    page, qs = paginate(request, customers, 10)
    return render(request, "customers/customer_list.html", {"page": page, "qs": qs, "q": q})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    orders = Order.objects.filter(customer=customer)[:10]
    return render(request, "customers/customer_detail.html", {"customer": customer, "orders": orders})


@login_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        messages.success(request, f"Customer '{customer.name}' added.")
        return redirect("customers:list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": "Add customer", "cancel_url": "customers:list",
         "submit_label": "Save customer", "icon": "bi-person-plus"},
    )


@login_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Customer '{customer.name}' updated.")
        return redirect("customers:list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": f"Edit customer: {customer.name}", "cancel_url": "customers:list",
         "submit_label": "Update customer", "icon": "bi-person-gear"},
    )


@admin_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        try:
            name = customer.name
            customer.delete()
            messages.success(request, f"Customer '{name}' deleted.")
        except ProtectedError:
            messages.error(request, f"Cannot delete '{customer.name}' because they have existing orders.")
        return redirect("customers:list")
    return render(
        request,
        "confirm_delete.html",
        {"object_label": "customer", "object_name": customer.name, "cancel_url": "customers:list",
         "warning": "Customers with existing orders cannot be deleted."},
    )
