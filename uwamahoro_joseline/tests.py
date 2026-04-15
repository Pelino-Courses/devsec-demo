from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:register")

    def test_registration_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create an account")

    def test_successful_registration(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))
        self.assertTrue(User.objects.filter(username="testuser").exists())
        self.assertTrue(Profile.objects.filter(user__username="testuser").exists())

    def test_registration_creates_profile(self):
        data = {
            "username": "profileuser",
            "email": "profile@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        self.client.post(self.url, data)
        user = User.objects.get(username="profileuser")
        self.assertTrue(hasattr(user, "profile"))

    def test_registration_with_mismatched_passwords(self):
        data = {
            "username": "baduser",
            "email": "bad@example.com",
            "password1": "SecurePass123!",
            "password2": "DifferentPass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_registration_with_duplicate_username(self):
        User.objects.create_user(username="taken", password="SomePass123!")
        data = {
            "username": "taken",
            "email": "taken@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="taken").count(), 1)

    def test_authenticated_user_redirected_from_register(self):
        User.objects.create_user(username="existing", password="Pass123!")
        self.client.login(username="existing", password="Pass123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))


class LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:login")
        self.user = User.objects.create_user(username="loginuser", password="TestPass123!")

    def test_login_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_successful_login(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))

    def test_failed_login_wrong_password(self):
        data = {"username": "loginuser", "password": "WrongPassword!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_failed_login_unknown_user(self):
        data = {"username": "nobody", "password": "TestPass123!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="loginuser", password="TestPass123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))

    def test_login_next_parameter_safe_redirect(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        safe_next = reverse("uwamahoro_joseline:profile")
        response = self.client.post(f"{self.url}?next={safe_next}", data)
        self.assertRedirects(response, safe_next)

    def test_login_next_parameter_rejects_external_url(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        response = self.client.post(
            self.url, {**data, "next": "http://evil.example.com/"}
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))


class LogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:logout")
        self.user = User.objects.create_user(username="logoutuser", password="TestPass123!")

    def test_logout_page_loads_for_authenticated_user(self):
        self.client.login(username="logoutuser", password="TestPass123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_successful_logout(self):
        self.client.login(username="logoutuser", password="TestPass123!")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:login"))
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertNotEqual(response.status_code, 200)


class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="authuser", password="TestPass123!")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_profile_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_password_change_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_accessible_when_authenticated(self):
        self.client.login(username="authuser", password="TestPass123!")
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_profile_accessible_when_authenticated(self):
        self.client.login(username="authuser", password="TestPass123!")
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:password_change")
        self.user = User.objects.create_user(username="pwuser", password="OldPass123!")
        self.client.login(username="pwuser", password="OldPass123!")

    def test_password_change_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change password")

    def test_successful_password_change(self):
        data = {
            "old_password": "OldPass123!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass456!"))

    def test_password_change_wrong_old_password(self):
        data = {
            "old_password": "WrongOld!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("NewSecurePass456!"))

    def test_session_preserved_after_password_change(self):
        data = {
            "old_password": "OldPass123!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        self.client.post(self.url, data)
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)


class ProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="profileuser", email="pf@example.com", password="TestPass123!"
        )
        self.client.login(username="profileuser", password="TestPass123!")

    def test_profile_page_shows_username(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertContains(response, "profileuser")

    def test_profile_page_shows_email(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertContains(response, "pf@example.com")

    def test_profile_auto_creates_if_missing(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
