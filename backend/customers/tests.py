from django.urls import reverse

from core.testing import BaseTestCase
from customers.models import Customer
from orders.services import create_order


class CustomerWebTests(BaseTestCase):
    def setUp(self):
        self.client.login(username="admin_t", password="Admin@12345")

    def test_add_edit_search_delete(self):
        self.client.post(reverse("customers:create"), {
            "name": "Maya", "phone": "9876543210", "email": "m@example.com", "address": "Kochi"})
        customer = Customer.objects.get(name="Maya")
        self.client.post(reverse("customers:update", args=[customer.pk]), {
            "name": "Maya K", "phone": "9876543210", "email": "m@example.com", "address": "Kochi"})
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Maya K")
        self.assertContains(self.client.get(reverse("customers:list"), {"q": "maya"}), "Maya K")
        self.client.post(reverse("customers:delete", args=[customer.pk]))
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())

    def test_invalid_phone_rejected(self):
        response = self.client.post(reverse("customers:create"), {"name": "Bad", "phone": "abc", "email": "", "address": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.filter(name="Bad").exists())

    def test_customer_with_orders_is_protected(self):
        create_order(customer=self.customer, items=[{"product": self.product.pk, "quantity": 1}], user=self.admin)
        self.client.post(reverse("customers:delete", args=[self.customer.pk]))
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())


class CustomerDeletePermissionTests(BaseTestCase):
    """Customer deletion: admin only, and never when the customer has orders."""

    def test_staff_cannot_delete_customer_web(self):
        self.client.login(username="staff_t", password="Staff@12345")
        self.assertEqual(self.client.get(reverse("customers:delete", args=[self.customer.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("customers:delete", args=[self.customer.pk])).status_code, 403)
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_admin_sees_confirmation_page_then_deletes(self):
        self.client.login(username="admin_t", password="Admin@12345")
        page = self.client.get(reverse("customers:delete", args=[self.customer.pk]))
        self.assertContains(page, "Delete this customer")
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())  # GET never deletes
        self.client.post(reverse("customers:delete", args=[self.customer.pk]))
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_delete_buttons_hidden_from_staff(self):
        self.client.login(username="staff_t", password="Staff@12345")
        self.assertNotContains(self.client.get(reverse("customers:list")), "/delete/")
        self.client.login(username="admin_t", password="Admin@12345")
        self.assertContains(self.client.get(reverse("customers:list")), "/delete/")

    def test_delete_nonexistent_customer_404(self):
        self.client.login(username="admin_t", password="Admin@12345")
        self.assertEqual(self.client.post(reverse("customers:delete", args=[99999])).status_code, 404)
