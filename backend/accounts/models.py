from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superusers created with `createsuperuser` are always Admin-role users.
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user with a simple role for role-based access control (RBAC)."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAFF = "staff", "Staff"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    phone = models.CharField(max_length=20, blank=True)

    objects = UserManager()

    class Meta:
        ordering = ["username"]

    @property
    def is_admin_role(self) -> bool:
        return bool(self.is_active and (self.is_superuser or self.role == self.Role.ADMIN))

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    def __str__(self):
        return self.username
