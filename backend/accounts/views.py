from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import paginate

from .decorators import admin_required
from .forms import LoginForm, RegisterForm, UserManageForm
from .models import User


class UserLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(auth_views.LogoutView):
    """Logout requires POST (Django 5)."""


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created successfully. You can now sign in.")
        return redirect("accounts:login")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    return render(request, "accounts/profile.html")


@admin_required
def user_list(request):
    q = request.GET.get("q", "").strip()
    users = User.objects.all()
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    page, qs = paginate(request, users, 10)
    return render(request, "accounts/user_list.html", {"page": page, "qs": qs, "q": q})


@admin_required
def user_update(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = UserManageForm(request.POST or None, instance=target)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        if target.pk == request.user.pk and (
            updated.role != User.Role.ADMIN and not target.is_superuser or not updated.is_active
        ):
            messages.error(request, "You cannot remove your own admin role or deactivate your own account.")
        else:
            updated.save()
            messages.success(request, f"User '{updated.username}' updated.")
            return redirect("accounts:user_list")
    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": f"Edit user: {target.username}",
            "cancel_url": "accounts:user_list",
            "submit_label": "Save user",
            "icon": "bi-person-gear",
        },
    )
