from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile

class RegistrationTestCase(TestCase):
    def test_register_success(self):
        # We ensure the password matches the default requirements
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(User.objects.count(), 1)
        self.assertRedirects(response, reverse('login'))

    def test_register_duplicate_email(self):
        User.objects.create_user(username='existing', email='test@example.com', password='pass')
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        # This will now be 200 because the form will catch the error
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'This email is already registered.')

class LoginTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='StrongPass123!'
        )

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_wrong_password(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_open_redirect_prevention(self):
        malicious_url = "https://hacker.com"
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
            'next': malicious_url
        })
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)

    def test_safe_internal_redirect(self):
        safe_url = "/profile/"
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'StrongPass123!',
            'next': safe_url
        })
        self.assertRedirects(response, safe_url, fetch_redirect_response=False)

class ProtectedPagesTestCase(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, "/login/?next=/dashboard/")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, "/login/?next=/profile/")

    def test_dashboard_accessible_when_logged_in(self):
        user = User.objects.create_user(username='protected_user', password='StrongPass123!')
        self.client.login(username='protected_user', password='StrongPass123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)