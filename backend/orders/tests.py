from decimal import Decimal

from django.urls import reverse

from core.testing import BaseTestCase
from inventory.models import StockTransaction
from orders.models import Order
from orders.services import OrderError, change_status, create_order


class OrderServiceTests(BaseTestCase):
    def test_create_order_calculates_totals_and_reduces_stock(self):
        order, _ = create_order(
            customer=self.customer, user=self.staff,
            items=[{"product": self.product.pk, "quantity": 3}, {"product": self.product2.pk, "quantity": 2}],
        )
        self.assertEqual(order.total_amount, Decimal("150.00") * 3 + Decimal("200.00") * 2)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.product.refresh_from_db(); self.product2.refresh_from_db()
        self.assertEqual((self.product.quantity, self.product2.quantity), (17, 8))
        self.assertEqual(StockTransaction.objects.filter(order=order, transaction_type="OUT").count(), 2)

    def test_insufficient_stock_rolls_back_everything(self):
        with self.assertRaises(OrderError):
            create_order(customer=self.customer, user=self.staff, items=[
                {"product": self.product.pk, "quantity": 5}, {"product": self.product2.pk, "quantity": 11}])
        self.product.refresh_from_db(); self.product2.refresh_from_db()
        self.assertEqual((self.product.quantity, self.product2.quantity), (20, 10))
        self.assertEqual(Order.objects.count(), 0)

    def test_invalid_lines_rejected(self):
        for items in ([], [{"product": self.product.pk, "quantity": 0}], [{"product": "x", "quantity": 1}],
                      [{"product": 99999, "quantity": 1}]):
            with self.assertRaises(OrderError):
                create_order(customer=self.customer, items=items)
        self.assertEqual(Order.objects.count(), 0)

    def test_duplicate_lines_are_merged(self):
        order, _ = create_order(customer=self.customer, items=[
            {"product": self.product.pk, "quantity": 2}, {"product": self.product.pk, "quantity": 3}])
        self.assertEqual(order.items.get().quantity, 5)

    def test_price_snapshot_survives_price_change(self):
        order, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 1}])
        self.product.selling_price = Decimal("999.00"); self.product.save()
        self.assertEqual(order.items.get().unit_price, Decimal("150.00"))

    def test_status_flow_and_cancel_restores_stock(self):
        order, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 4}])
        change_status(order.pk, "confirmed"); change_status(order.pk, "completed")
        with self.assertRaises(OrderError):
            change_status(order.pk, "cancelled")  # completed orders are final
        order2, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 6}])
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)
        change_status(order2.pk, "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 16)
        with self.assertRaises(OrderError):
            change_status(order2.pk, "cancelled")  # cannot cancel twice (no double restore)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 16)

    def test_low_stock_products_returned(self):
        _, low = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 16}])
        self.assertEqual([p.pk for p in low], [self.product.pk])


class OrderWebTests(BaseTestCase):
    def setUp(self):
        self.client.login(username="staff_t", password="Staff@12345")

    def test_create_order_page_multiple_products(self):
        response = self.client.post(reverse("orders:create"), {
            "customer": self.customer.pk, "notes": "rush",
            "product": [self.product.pk, self.product2.pk], "quantity": ["2", "1"]})
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:detail", args=[order.pk]))
        self.assertEqual(order.total_amount, Decimal("500.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 18)

    def test_order_with_too_much_quantity_shows_error(self):
        response = self.client.post(reverse("orders:create"), {
            "customer": self.customer.pk, "product": [self.product.pk], "quantity": ["999"]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insufficient stock")
        self.assertEqual(Order.objects.count(), 0)

    def test_history_detail_and_status_change(self):
        order, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 1}], user=self.staff)
        self.assertContains(self.client.get(reverse("orders:list")), order.order_number)
        self.assertContains(self.client.get(reverse("orders:detail", args=[order.pk])), "Widget")
        self.client.post(reverse("orders:status", args=[order.pk]), {"status": "confirmed"})
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")

    def test_status_change_requires_post(self):
        order, _ = create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 1}])
        self.assertEqual(self.client.get(reverse("orders:status", args=[order.pk])).status_code, 405)
