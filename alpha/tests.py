from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class UASAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.protected_url = reverse('protected_view')

    def test_login_success(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'testpassword'})
        self.assertRedirects(response, reverse('profile'))

    def test_login_failure(self):
        response = self.client.post(self.login_url, {'username': 'testuser', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    def test_protected_view_redirects_unauthenticated(self):
        response = self.client.get(self.protected_url)
        self.assertRedirects(response, f"{self.login_url}?next={self.protected_url}")

    def test_protected_view_allows_authenticated(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(self.protected_url)
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(self.logout_url)
        self.assertRedirects(response, self.login_url)
