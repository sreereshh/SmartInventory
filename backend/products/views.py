from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import admin_required
from core.utils import paginate
from inventory.models import StockTransaction
from inventory.services import create_product_with_opening_stock

from .forms import CategoryForm, ProductForm
from .models import Category, Product


# ----------------------------------------------------------------- products
@login_required
def product_list(request):
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    products = Product.objects.select_related("category")
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(code__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )
    if category.isdigit():
        products = products.filter(category_id=int(category))
    if status == "low":
        products = products.filter(quantity__lte=F("min_stock_level"), quantity__gt=0)
    elif status == "out":
        products = products.filter(quantity=0)
    elif status == "ok":
        products = products.filter(quantity__gt=F("min_stock_level"))

    page, qs = paginate(request, products, 10)
    return render(
        request,
        "products/product_list.html",
        {
            "page": page,
            "qs": qs,
            "q": q,
            "category": category,
            "status": status,
            "categories": Category.objects.all(),
        },
    )


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    history = StockTransaction.objects.filter(product=product).select_related("created_by")[:10]
    return render(request, "products/product_detail.html", {"product": product, "history": history})


@login_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        create_product_with_opening_stock(product, form.cleaned_data.get("quantity") or 0, request.user)
        messages.success(request, f"Product '{product.name}' created.")
        return redirect("products:detail", pk=product.pk)
    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": "Add product",
            "cancel_url": "products:list",
            "submit_label": "Save product",
            "icon": "bi-box-seam",
        },
    )


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Product '{product.name}' updated.")
        return redirect("products:detail", pk=product.pk)
    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": f"Edit product: {product.name}",
            "cancel_url": "products:list",
            "submit_label": "Update product",
            "icon": "bi-pencil-square",
            "info": f"Current stock: {product.quantity}. To change stock use Stock In / Stock Out so the history stays accurate.",
        },
    )


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        try:
            name = product.name
            product.delete()
            messages.success(request, f"Product '{name}' deleted.")
        except ProtectedError:
            messages.error(
                request,
                f"Cannot delete '{product.name}' because it appears in existing orders.",
            )
        return redirect("products:list")
    return render(
        request,
        "confirm_delete.html",
        {
            "object_label": "product",
            "object_name": str(product),
            "cancel_url": "products:list",
            "warning": "Its stock history will also be removed. Products that were ordered cannot be deleted.",
        },
    )


# --------------------------------------------------------------- categories
@login_required
def category_list(request):
    q = request.GET.get("q", "").strip()
    categories = Category.objects.annotate(product_count=Count("products"))
    if q:
        categories = categories.filter(name__icontains=q)
    page, qs = paginate(request, categories, 10)
    return render(request, "products/category_list.html", {"page": page, "qs": qs, "q": q})


@login_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category created.")
        return redirect("products:category_list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": "Add category", "cancel_url": "products:category_list",
         "submit_label": "Save category", "icon": "bi-tags"},
    )


@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect("products:category_list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": f"Edit category: {category.name}", "cancel_url": "products:category_list",
         "submit_label": "Update category", "icon": "bi-tags"},
    )


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        try:
            category.delete()
            messages.success(request, "Category deleted.")
        except ProtectedError:
            messages.error(request, "Cannot delete a category that still has products. Move or delete them first.")
        return redirect("products:category_list")
    return render(
        request,
        "confirm_delete.html",
        {"object_label": "category", "object_name": category.name, "cancel_url": "products:category_list",
         "warning": "Categories that contain products cannot be deleted."},
    )
