"""
Tests for open redirect protection in the Aline UAS application.
Verifies that the 'next' parameter is correctly validated during login.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from aline.models import UserProfile

class OpenRedirectProtectionTestCase(TestCase):
    """Test cases for preventing open redirect vulnerabilities."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse('aline:login')
        self.dashboard_url = reverse('aline:dashboard')
        self.username = 'testuser'
        self.password = 'SecurePass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='test@example.com'
        )
        # Create profile since dashboard requires it
        UserProfile.objects.create(user=self.user)

    def test_safe_internal_redirect(self):
        """
        Verify that hitting a safe internal URL via 'next' works correctly.
        """
        safe_url = reverse('aline:profile')
        login_data = {
            'username': self.username,
            'password': self.password,
        }
        
        # Test both GET and POST for 'next'
        # GET next
        response = self.client.post(f"{self.login_url}?next={safe_url}", login_data)
        self.assertRedirects(response, safe_url)
        
        self.client.logout()
        
        # POST next
        login_data['next'] = safe_url
        response = self.client.post(self.login_url, login_data)
        self.assertRedirects(response, safe_url)

    def test_unsafe_external_redirect_is_rejected(self):
        """
        Verify that unsafe external redirections are caught and defaulted to a safe internal URL.
        """
        unsafe_urls = [
            'http://malicious.com',
            'https://malicious.net/login',
            '//malicious-domain.com',
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>',
        ]
        
        for unsafe_url in unsafe_urls:
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            
            # Test via GET next parameter
            response = self.client.post(f"{self.login_url}?next={unsafe_url}", login_data)
            
            # Should redirect to default dashboard instead of unsafe URL
            self.assertRedirects(response, self.dashboard_url)
            self.client.logout()

    def test_complex_unsafe_redirects(self):
        """
        Verify more complex or obfuscated unsafe redirect attempts are rejected.
        """
        # Testing protocol-relative URLs and other bypass attempts
        complex_unsafe = [
            '  https://malicious.com',  # Leading whitespace
            r'/\/\malicious.com',        # Obfuscated slashes
            'https:malicious.com',       # Missing slashes but some parsers might follow
        ]
        
        for unsafe_url in complex_unsafe:
            login_data = {
                'username': self.username,
                'password': self.password,
            }
            response = self.client.post(f"{self.login_url}?next={unsafe_url}", login_data)
            self.assertRedirects(response, self.dashboard_url)
            self.client.logout()
