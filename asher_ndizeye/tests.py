from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile


class RegistrationTestCase(TestCase):
    def test_register_success(self):
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
        self.assertFormError(response, 'form', 'email', 'This email is already registered.')

    def test_register_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'StrongPass123!',
            'password2': 'WrongPass123!',
        })
        self.assertEqual(User.objects.count(), 0)


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


class ProtectedPagesTestCase(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"/login/?next=/")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f"/login/?next=/profile/")

    def test_dashboard_accessible_when_logged_in(self):
        User.objects.create_user(username='testuser', password='StrongPass123!')
        self.client.login(username='testuser', password='StrongPass123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)