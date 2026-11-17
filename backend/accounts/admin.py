from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_active", "is_superuser")
    list_filter = ("role", "is_active", "is_superuser")
    fieldsets = DjangoUserAdmin.fieldsets + (("Role", {"fields": ("role", "phone")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (("Role", {"fields": ("role", "phone")}),)
