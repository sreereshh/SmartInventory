from decimal import Decimal

from django.urls import reverse

from core.testing import BaseTestCase
from inventory.models import StockTransaction
from products.models import Category, Product


class ProductWebTests(BaseTestCase):
    def setUp(self):
        self.client.login(username="admin_t", password="Admin@12345")

    def test_add_product_logs_opening_stock(self):
        response = self.client.post(reverse("products:create"), {
            "name": "Phone", "code": "ph-1", "category": self.category.pk, "purchase_price": "100",
            "selling_price": "150", "quantity": "12", "min_stock_level": "3", "description": "x",
        })
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(code="PH-1")  # code upper-cased
        self.assertEqual(product.quantity, 12)
        txn = StockTransaction.objects.get(product=product)
        self.assertEqual((txn.transaction_type, txn.quantity, txn.reason), ("IN", 12, "opening"))

    def test_duplicate_code_rejected(self):
        response = self.client.post(reverse("products:create"), {
            "name": "Dup", "code": "p-001", "category": self.category.pk, "purchase_price": "1",
            "selling_price": "2", "quantity": "0", "min_stock_level": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name="Dup").exists())

    def test_edit_product_does_not_change_quantity(self):
        response = self.client.post(reverse("products:update", args=[self.product.pk]), {
            "name": "Widget v2", "code": "P-001", "category": self.category.pk, "purchase_price": "100",
            "selling_price": "175", "min_stock_level": "5", "quantity": "999", "description": "",
        })
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Widget v2")
        self.assertEqual(self.product.selling_price, Decimal("175"))
        self.assertEqual(self.product.quantity, 20)

    def test_delete_product(self):
        product = self.make_product("DEL-1", "Deletable")
        response = self.client.post(reverse("products:delete", args=[product.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_staff_cannot_delete_product(self):
        self.client.logout()
        self.client.login(username="staff_t", password="Staff@12345")
        response = self.client.post(reverse("products:delete", args=[self.product.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_search_products(self):
        response = self.client.get(reverse("products:list"), {"q": "gizmo"})
        self.assertContains(response, "Gizmo")
        self.assertNotContains(response, "Widget")

    def test_category_crud(self):
        self.client.post(reverse("products:category_create"), {"name": "Tools", "description": ""})
        category = Category.objects.get(name="Tools")
        self.client.post(reverse("products:category_update", args=[category.pk]), {"name": "Hand Tools", "description": ""})
        category.refresh_from_db()
        self.assertEqual(category.name, "Hand Tools")
        self.client.post(reverse("products:category_delete", args=[category.pk]))
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_category_with_products_cannot_be_deleted(self):
        self.client.post(reverse("products:category_delete", args=[self.category.pk]))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
