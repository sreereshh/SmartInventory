"""Shared fixtures for the automated test-suite."""
from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from customers.models import Customer
from inventory.services import create_product_with_opening_stock
from products.models import Category, Product


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin_t", "a@example.com", "Admin@12345")
        cls.staff = User.objects.create_user("staff_t", "s@example.com", "Staff@12345", role=User.Role.STAFF)
        cls.category = Category.objects.create(name="Gadgets")
        cls.customer = Customer.objects.create(name="Test Customer", phone="+91 90000 00000", email="c@example.com")
        cls.product = cls.make_product("P-001", "Widget", qty=20, minimum=5)
        cls.product2 = cls.make_product("P-002", "Gizmo", qty=10, minimum=5, selling="200.00", purchase="120.00")

    @classmethod
    def make_product(cls, code, name, qty=10, minimum=5, selling="150.00", purchase="100.00"):
        product = Product(
            name=name, code=code, category=cls.category,
            purchase_price=Decimal(purchase), selling_price=Decimal(selling), min_stock_level=minimum,
        )
        return create_product_with_opening_stock(product, qty, cls.admin)
