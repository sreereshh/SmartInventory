from decimal import Decimal

from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.testing import BaseTestCase
from orders.models import Order


class ApiTestCase(BaseTestCase):
    def setUp(self):
        self.api = APIClient()

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")


class AuthApiTests(ApiTestCase):
    def test_login_returns_token(self):
        r = self.api.post(reverse("api-login"), {"username": "admin_t", "password": "Admin@12345"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["token"])
        self.assertTrue(r.data["user"]["is_admin"])

    def test_bad_login_is_401(self):
        r = self.api.post(reverse("api-login"), {"username": "admin_t", "password": "nope"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_endpoints_need_token(self):
        for name in ("product-list", "customer-list", "order-list", "api-dashboard", "api-stock", "api-me"):
            self.assertEqual(self.api.get(reverse(name)).status_code, 401, name)

    def test_register_creates_staff(self):
        r = self.api.post(reverse("api-register"), {
            "username": "apiuser", "email": "x@example.com", "password": "Str0ng!Pass#9"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["user"]["role"], "staff")

    def test_register_weak_password_400(self):
        r = self.api.post(reverse("api-register"), {"username": "weak", "email": "w@example.com", "password": "123"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_logout_invalidates_token(self):
        self.auth(self.staff)
        self.assertEqual(self.api.post(reverse("api-logout")).status_code, 200)
        self.assertEqual(self.api.get(reverse("api-me")).status_code, 401)


class CatalogueApiTests(ApiTestCase):
    def test_product_crud_and_rbac(self):
        self.auth(self.staff)
        payload = {"name": "New", "code": "n-1", "category": self.category.pk, "purchase_price": "10.00",
                   "selling_price": "15.00", "quantity": 7, "min_stock_level": 2}
        r = self.api.post(reverse("product-list"), payload, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data["id"]
        self.assertEqual((r.data["code"], r.data["quantity"]), ("N-1", 7))
        r = self.api.patch(reverse("product-detail", args=[pid]), {"selling_price": "20.00"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.api.delete(reverse("product-detail", args=[pid])).status_code, 403)
        self.auth(self.admin)
        self.assertEqual(self.api.delete(reverse("product-detail", args=[pid])).status_code, 204)

    def test_product_validation(self):
        self.auth(self.admin)
        bad = {"name": "B", "code": "p-001", "category": self.category.pk, "purchase_price": "10",
               "selling_price": "5", "min_stock_level": 1}
        r = self.api.post(reverse("product-list"), bad, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("errors", r.data)
        self.assertIn("detail", r.data)

    def test_quantity_cannot_be_patched_directly(self):
        self.auth(self.admin)
        r = self.api.patch(reverse("product-detail", args=[self.product.pk]), {"quantity": 500}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_search_and_filter(self):
        self.auth(self.staff)
        r = self.api.get(reverse("product-list"), {"search": "gizmo"})
        self.assertEqual([p["code"] for p in r.data["results"]], ["P-002"])
        self.assertEqual(self.api.get(reverse("product-list"), {"status": "low"}).data["count"], 0)

    def test_delete_ordered_product_is_409(self):
        self.auth(self.admin)
        self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 1}]}, format="json")
        self.assertEqual(self.api.delete(reverse("product-detail", args=[self.product.pk])).status_code, 409)

    def test_customer_crud(self):
        self.auth(self.staff)
        r = self.api.post(reverse("customer-list"), {"name": "Z", "phone": "9999999999", "email": "", "address": ""}, format="json")
        self.assertEqual(r.status_code, 201)
        r = self.api.post(reverse("customer-list"), {"name": "Z", "phone": "abc"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.api.get(reverse("customer-list"), {"search": "Test"}).data["count"], 1)

    def test_customer_delete_rules(self):
        from customers.models import Customer
        from rest_framework.authtoken.models import Token  # noqa: F401
        fresh = Customer.objects.create(name="Temp", phone="9111111111")
        self.auth(self.staff)
        self.assertEqual(self.api.delete(reverse("customer-detail", args=[fresh.pk])).status_code, 403)
        self.auth(self.admin)
        self.assertEqual(self.api.delete(reverse("customer-detail", args=[fresh.pk])).status_code, 204)
        self.assertFalse(Customer.objects.filter(pk=fresh.pk).exists())
        self.assertEqual(self.api.delete(reverse("customer-detail", args=[fresh.pk])).status_code, 404)
        self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 1}]}, format="json")
        r = self.api.delete(reverse("customer-detail", args=[self.customer.pk]))
        self.assertEqual(r.status_code, 409)
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_not_found_is_404(self):
        self.auth(self.staff)
        self.assertEqual(self.api.get(reverse("product-detail", args=[99999])).status_code, 404)


class InventoryApiTests(ApiTestCase):
    def test_stock_in_out_and_validation(self):
        self.auth(self.staff)
        r = self.api.post(reverse("api-stock-in"), {"product": self.product.pk, "quantity": 5}, format="json")
        self.assertEqual((r.status_code, r.data["current_quantity"]), (201, 25))
        r = self.api.post(reverse("api-stock-out"), {"product": self.product.pk, "quantity": 21 + 4}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["current_quantity"], 0)
        self.assertTrue(r.data["low_stock_alert"])
        r = self.api.post(reverse("api-stock-out"), {"product": self.product.pk, "quantity": 1}, format="json")
        self.assertEqual(r.status_code, 400)  # would go negative
        r = self.api.post(reverse("api-stock-in"), {"product": self.product.pk, "quantity": 0}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_stock_listing_low_stock_and_history(self):
        self.auth(self.staff)
        self.api.post(reverse("api-stock-out"), {"product": self.product.pk, "quantity": 18}, format="json")
        low = self.api.get(reverse("api-low-stock"))
        self.assertEqual([p["code"] for p in low.data["results"]], ["P-001"])
        self.assertEqual(self.api.get(reverse("api-stock")).data["count"], 2)
        history = self.api.get(reverse("api-transactions"), {"product": self.product.pk, "type": "OUT"})
        self.assertEqual(history.data["count"], 1)


class OrderApiTests(ApiTestCase):
    def test_create_order_reduces_stock(self):
        self.auth(self.staff)
        r = self.api.post(reverse("order-list"), {"customer": self.customer.pk, "notes": "n", "items": [
            {"product": self.product.pk, "quantity": 2}, {"product": self.product2.pk, "quantity": 3}]}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(str(r.data["total_amount"])), Decimal("900.00"))
        self.assertEqual(len(r.data["items"]), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 18)
        self.assertEqual(self.api.get(reverse("order-detail", args=[r.data["id"]])).status_code, 200)
        self.assertEqual(self.api.get(reverse("order-list")).data["count"], 1)

    def test_insufficient_stock_400_and_nothing_saved(self):
        self.auth(self.staff)
        r = self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 1}, {"product": self.product2.pk, "quantity": 500}]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Insufficient stock", r.data["detail"])
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 20)

    def test_empty_and_duplicate_items_400(self):
        self.auth(self.staff)
        self.assertEqual(self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": []}, format="json").status_code, 400)
        dup = {"customer": self.customer.pk, "items": [{"product": self.product.pk, "quantity": 1}] * 2}
        self.assertEqual(self.api.post(reverse("order-list"), dup, format="json").status_code, 400)

    def test_status_change_and_cancel(self):
        self.auth(self.staff)
        order = self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 5}]}, format="json").data
        url = reverse("order-set-status", args=[order["id"]])
        self.assertEqual(self.api.post(url, {"status": "completed"}, format="json").status_code, 400)  # must confirm first
        self.assertEqual(self.api.post(url, {"status": "cancelled"}, format="json").status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 20)

    def test_orders_cannot_be_deleted_or_edited(self):
        self.auth(self.admin)
        order = self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 1}]}, format="json").data
        self.assertEqual(self.api.delete(reverse("order-detail", args=[order["id"]])).status_code, 405)


class DashboardReportApiTests(ApiTestCase):
    def test_dashboard_from_database(self):
        self.auth(self.staff)
        self.api.post(reverse("order-list"), {"customer": self.customer.pk, "items": [
            {"product": self.product.pk, "quantity": 2}]}, format="json")
        r = self.api.get(reverse("api-dashboard"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["total_products"], r.data["total_customers"], r.data["total_orders"]), (2, 1, 1))
        self.assertEqual(Decimal(str(r.data["total_sales"])), Decimal("300.00"))
        self.assertEqual(len(r.data["recent_orders"]), 1)

    def test_reports(self):
        self.auth(self.staff)
        for name in ("api-report-daily", "api-report-monthly", "api-report-total", "api-report-inventory",
                     "api-report-low-stock", "api-report-orders"):
            self.assertEqual(self.api.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.api.get(reverse("api-report-daily"), {"date": "bad"}).status_code, 400)
        self.assertEqual(self.api.get(reverse("api-report-monthly"), {"month": "2026-13"}).status_code, 400)

    def test_swagger_docs_available(self):
        self.assertEqual(self.api.get(reverse("schema")).status_code, 200)
        self.assertEqual(self.api.get(reverse("swagger-ui")).status_code, 200)
