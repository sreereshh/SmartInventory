from django.urls import reverse

from accounts.models import User
from core.testing import BaseTestCase


class AuthenticationTests(BaseTestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_login_and_logout(self):
        self.assertTrue(self.client.login(username="admin_t", password="Admin@12345"))
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_login_view_posts(self):
        response = self.client.post(reverse("accounts:login"), {"username": "staff_t", "password": "Staff@12345"})
        self.assertRedirects(response, reverse("dashboard"))

    def test_bad_password_rejected(self):
        response = self.client.post(reverse("accounts:login"), {"username": "staff_t", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_registration_creates_staff_with_hashed_password(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newbie", "first_name": "New", "last_name": "Bie", "email": "n@example.com",
            "password1": "Str0ng!Pass#9", "password2": "Str0ng!Pass#9",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newbie")
        self.assertEqual(user.role, User.Role.STAFF)
        self.assertNotEqual(user.password, "Str0ng!Pass#9")
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_staff_cannot_open_user_management(self):
        self.client.login(username="staff_t", password="Staff@12345")
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)

    def test_admin_can_open_user_management(self):
        self.client.login(username="admin_t", password="Admin@12345")
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 200)
