from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class OpenRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.login_url = reverse('login')
        self.register_url = reverse('register')

    def test_login_redirects_to_internal_url(self):
        """Verify that 'next=/profile/' redirects correctly to the internal profile page."""
        response = self.client.post(self.login_url + '?next=/accounts/profile/', {
            'username': 'testuser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        # Verify it redirects to /accounts/profile/
        self.assertIn('/accounts/profile/', response.url)

    def test_login_blocks_external_redirect(self):
        """Verify that 'next=https://malicious.com' is rejected and redirects to default profile."""
        response = self.client.post(self.login_url + '?next=https://malicious.com', {
            'username': 'testuser',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        # Verify it DOES NOT redirect to malicious.com
        self.assertNotIn('malicious.com', response.url)
        # Verify it redirects to the safe fallback /accounts/profile/
        self.assertIn('/accounts/profile/', response.url)

    def test_registration_redirects_to_internal_url(self):
        """Verify that registration correctly uses safe redirect targets."""
        response = self.client.post(self.register_url + '?next=/accounts/login/', {
            'username': 'newuser',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_registration_blocks_external_redirect(self):
        """Verify that registration blocks open redirects."""
        response = self.client.post(self.register_url + '?next=http://evil.com', {
            'username': 'attacker',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.com', response.url)
        # Should fallback to login
        self.assertIn('/accounts/login/', response.url)
