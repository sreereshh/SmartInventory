from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from core.testing import BaseTestCase
from orders.services import change_status, create_order
from reports import services


class ReportTests(BaseTestCase):
    def setUp(self):
        self.order, _ = create_order(customer=self.customer, user=self.staff, items=[
            {"product": self.product.pk, "quantity": 2}, {"product": self.product2.pk, "quantity": 1}])
        cancelled, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 5}])
        change_status(cancelled.pk, "cancelled")
        self.client.login(username="staff_t", password="Staff@12345")

    def test_total_sales_excludes_cancelled(self):
        report = services.total_sales_report()
        self.assertEqual(report["summary"]["total_sales"], Decimal("500.00"))
        self.assertEqual(report["summary"]["order_count"], 1)
        self.assertEqual(report["cancelled_orders"], 1)

    def test_gross_profit(self):
        # (150-100)*2 + (200-120)*1 = 180
        self.assertEqual(services.total_sales_report()["summary"]["gross_profit"], Decimal("180.00"))

    def test_daily_and_monthly(self):
        today = timezone.localdate()
        self.assertEqual(services.daily_report(today)["summary"]["total_sales"], Decimal("500.00"))
        self.assertEqual(services.monthly_report(today.year, today.month)["summary"]["order_count"], 1)

    def test_inventory_and_low_stock(self):
        inv = services.inventory_report()
        self.assertEqual(inv["summary"]["total_units"], 18 + 9)  # 20-2 and 10-1; the cancelled order was restored
        self.assertEqual(services.low_stock_report()["summary"]["low_stock_count"], 0)

    def test_dashboard_matches_database(self):
        data = services.dashboard_data()
        self.assertEqual(data["total_products"], 2)
        self.assertEqual(data["total_customers"], 1)
        self.assertEqual(data["total_orders"], 2)
        self.assertEqual(data["total_sales"], Decimal("500.00"))

    def test_all_report_pages_render(self):
        for name in ("index", "daily", "monthly", "total", "inventory", "low_stock", "orders"):
            response = self.client.get(reverse(f"reports:{name}"))
            self.assertEqual(response.status_code, 200, name)

    def test_dashboard_page_shows_numbers(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
