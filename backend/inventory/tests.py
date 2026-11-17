from django.urls import reverse

from core.testing import BaseTestCase
from inventory.models import StockTransaction
from inventory.services import StockError, apply_stock


class StockServiceTests(BaseTestCase):
    def test_stock_in_updates_quantity_and_history(self):
        txn = apply_stock(product_id=self.product.pk, quantity=5, transaction_type="IN", reason="purchase", user=self.admin)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 25)
        self.assertEqual((txn.quantity_before, txn.quantity_after), (20, 25))

    def test_stock_out_updates_quantity(self):
        apply_stock(product_id=self.product.pk, quantity=8, transaction_type="OUT", reason="damage", user=self.admin)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 12)

    def test_negative_stock_is_prevented(self):
        with self.assertRaises(StockError):
            apply_stock(product_id=self.product.pk, quantity=21, transaction_type="OUT", reason="damage")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 20)
        self.assertEqual(StockTransaction.objects.filter(product=self.product, transaction_type="OUT").count(), 0)

    def test_zero_and_invalid_quantities_rejected(self):
        for bad in (0, -3, "5", True):
            with self.assertRaises(StockError):
                apply_stock(product_id=self.product.pk, quantity=bad, transaction_type="IN", reason="purchase")


class StockWebTests(BaseTestCase):
    def setUp(self):
        self.client.login(username="staff_t", password="Staff@12345")

    def test_stock_in_form(self):
        response = self.client.post(reverse("inventory:stock_in"), {
            "product": self.product.pk, "quantity": 10, "reason": "purchase", "note": "delivery"})
        self.assertRedirects(response, reverse("inventory:stock_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 30)

    def test_stock_out_form_blocks_overdraw(self):
        response = self.client.post(reverse("inventory:stock_out"), {
            "product": self.product.pk, "quantity": 500, "reason": "damage", "note": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Insufficient stock")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 20)

    def test_low_stock_alert_message(self):
        response = self.client.post(reverse("inventory:stock_out"), {
            "product": self.product.pk, "quantity": 17, "reason": "damage", "note": ""}, follow=True)
        self.assertContains(response, "Low stock alert")

    def test_stock_pages_render(self):
        for name in ("inventory:stock_list", "inventory:stock_history"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertContains(self.client.get(reverse("inventory:stock_history")), "Widget")
