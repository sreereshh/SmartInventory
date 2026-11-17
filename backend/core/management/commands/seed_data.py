"""
Create demo data for local testing:

    python manage.py seed_data            # only if the database has no products yet
    python manage.py seed_data --force    # wipe products/customers/orders and re-seed

Sample logins (LOCAL TESTING ONLY):
    admin / Admin@12345   (Admin role, superuser)
    staff / Staff@12345   (Staff role)
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from customers.models import Customer
from inventory.models import StockTransaction
from inventory.services import create_product_with_opening_stock
from orders.models import Order, OrderItem
from orders.services import OrderError, change_status, create_order
from products.models import Category, Product

CATEGORIES = [
    ("Electronics", "Phones, chargers and gadgets"),
    ("Computer Accessories", "Keyboards, mice, storage and cables"),
    ("Office Supplies", "Stationery and daily office needs"),
    ("Furniture", "Desks, chairs and storage"),
    ("Home & Kitchen", "Appliances and kitchen tools"),
]

# name, code, category, purchase, selling, opening qty, min level
PRODUCTS = [
    ("Wireless Mouse", "ELE-001", "Computer Accessories", "350.00", "599.00", 8, 10),      # low from the start
    ("Mechanical Keyboard", "ELE-002", "Computer Accessories", "1800.00", "2799.00", 40, 10),
    ("USB-C Charger 30W", "ELE-003", "Electronics", "450.00", "799.00", 120, 20),
    ("Bluetooth Speaker", "ELE-004", "Electronics", "1200.00", "1999.00", 35, 8),
    ("Noise Cancelling Headphones", "ELE-005", "Electronics", "3200.00", "4999.00", 18, 5),
    ("64GB Pen Drive", "CMP-001", "Computer Accessories", "380.00", "649.00", 90, 15),
    ("HDMI Cable 2m", "CMP-002", "Computer Accessories", "120.00", "249.00", 150, 25),
    ("A4 Copier Paper (500 sheets)", "OFF-001", "Office Supplies", "260.00", "349.00", 200, 40),
    ("Ball Pen Pack (10)", "OFF-002", "Office Supplies", "45.00", "80.00", 300, 50),
    ("Spiral Notebook A5", "OFF-003", "Office Supplies", "30.00", "60.00", 0, 30),             # out of stock
    ("Ergonomic Office Chair", "FUR-001", "Furniture", "5200.00", "7999.00", 14, 4),
    ("Standing Desk", "FUR-002", "Furniture", "9500.00", "13999.00", 6, 3),
    ("Electric Kettle 1.5L", "HK-001", "Home & Kitchen", "650.00", "999.00", 45, 10),
    ("Air Fryer 4L", "HK-002", "Home & Kitchen", "3400.00", "4999.00", 12, 5),
    ("LED Desk Lamp", "HK-003", "Home & Kitchen", "420.00", "749.00", 9, 10),                  # low
    ("Laptop Backpack", "ACC-001", "Computer Accessories", "700.00", "1299.00", 55, 10),
]

CUSTOMERS = [
    ("Arun Menon", "+91 90000 10001", "arun.menon@example.com", "12 Beach Road, Kozhikode, Kerala"),
    ("Fathima Rahman", "+91 90000 10002", "fathima.r@example.com", "45 Palayam, Kozhikode, Kerala"),
    ("Vishnu Nair", "+91 90000 10003", "vishnu.nair@example.com", "8 MG Road, Kochi, Kerala"),
    ("Anjali Das", "+91 90000 10004", "anjali.das@example.com", "21 Park Avenue, Thrissur, Kerala"),
    ("Joseph Mathew", "+91 90000 10005", "joseph.m@example.com", "3 Church Street, Kottayam, Kerala"),
    ("Sneha Pillai", "+91 90000 10006", "sneha.p@example.com", "77 Hill View, Wayanad, Kerala"),
    ("Techno Traders", "+91 90000 10007", "orders@technotraders.example.com", "Unit 5, Industrial Estate, Malappuram"),
    ("Greenleaf Stationers", "+91 90000 10008", "buy@greenleaf.example.com", "Market Road, Kannur, Kerala"),
]


class Command(BaseCommand):
    help = "Create demo users, products, customers and orders for local testing."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Delete existing catalogue/orders and re-seed.")

    def handle(self, *args, **options):
        self._ensure_users()

        if Product.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING("Sample data already present – use --force to reseed."))
            return

        with transaction.atomic():
            if options["force"]:
                OrderItem.objects.all().delete()
                StockTransaction.objects.all().delete()
                Order.objects.all().delete()
                Product.objects.all().delete()
                Category.objects.all().delete()
                Customer.objects.all().delete()
            admin = User.objects.get(username="admin")
            categories = {name: Category.objects.create(name=name, description=desc) for name, desc in CATEGORIES}
            for name, code, cat, buy, sell, qty, minimum in PRODUCTS:
                product = Product(
                    name=name, code=code, category=categories[cat], purchase_price=Decimal(buy),
                    selling_price=Decimal(sell), min_stock_level=minimum,
                    description=f"{name} – sample product for demo data.",
                )
                create_product_with_opening_stock(product, qty, admin)
            customers = [Customer.objects.create(name=n, phone=p, email=e, address=a) for n, p, e, a in CUSTOMERS]

        self._create_orders(customers, User.objects.get(username="staff"))
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Category.objects.count()} categories, {Product.objects.count()} products, "
            f"{Customer.objects.count()} customers and {Order.objects.count()} orders."
        ))
        self.stdout.write("Login: admin / Admin@12345  |  staff / Staff@12345  (local testing only)")

    # ------------------------------------------------------------------
    def _ensure_users(self):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "Admin@12345",
                                          first_name="Site", last_name="Admin")
            self.stdout.write("Created admin user (admin / Admin@12345).")
        if not User.objects.filter(username="staff").exists():
            User.objects.create_user("staff", "staff@example.com", "Staff@12345",
                                     first_name="Sam", last_name="Staff", role=User.Role.STAFF)
            self.stdout.write("Created staff user (staff / Staff@12345).")

    def _create_orders(self, customers, user):
        rng = random.Random(42)
        in_stock = list(Product.objects.filter(quantity__gt=20))
        now = timezone.now()
        created = 0
        for i in range(26):
            lines = [
                {"product": p.pk, "quantity": rng.randint(1, 3)}
                for p in rng.sample(in_stock, k=rng.randint(1, 3))
            ]
            try:
                order, _low = create_order(customer=rng.choice(customers), items=lines, user=user,
                                           notes="Sample order" if i % 4 == 0 else "")
            except OrderError:
                continue
            created += 1
            days_ago = rng.randint(0, 40) if i < 24 else 0
            when = now - timedelta(days=days_ago, hours=rng.randint(0, 8), minutes=rng.randint(0, 59))
            # Progress most older orders; cancel two for realistic data.
            if i in (5, 11):
                change_status(order.pk, Order.Status.CANCELLED, user)
            elif days_ago > 3:
                change_status(order.pk, Order.Status.CONFIRMED, user)
                change_status(order.pk, Order.Status.COMPLETED, user)
            elif days_ago > 1:
                change_status(order.pk, Order.Status.CONFIRMED, user)
            # Back-date order and its stock transactions so reports have history.
            Order.objects.filter(pk=order.pk).update(created_at=when)
            StockTransaction.objects.filter(order=order).update(created_at=when)
        self.stdout.write(f"Created {created} sample orders.")
