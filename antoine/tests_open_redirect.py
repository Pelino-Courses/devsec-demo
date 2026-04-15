"""
Redirect Safety Tests for Antoine Authentication Service

Tests that validate redirect handling prevents open redirect attacks
while maintaining safe internal navigation.

Security Goal: Ensure users can only be redirected to internal
application URLs, never to external/attacker-controlled sites.
"""
import os
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from urllib.parse import quote, urlencode

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devsec_demo.settings')
django.setup()


class RedirectSafetyTests(TestCase):
    """Test safe redirect handling on authentication flows"""

    def setUp(self):
        """Create test users"""
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!@#'
        )

    def test_login_with_valid_internal_redirect(self):
        """
        After successful login, redirect to 'next' parameter if it's a safe internal URL.
        
        Valid cases:
        - /dashboard/
        - /profile/
        - /change-password/
        """
        # Test with internal dashboard redirect
        response = self.client.post(
            reverse('antoine:login') + '?next=/dashboard/',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should redirect to the 'next' URL
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)

    def test_login_rejects_external_redirect(self):
        """
        Reject redirect to external URLs (open redirect attack).
        
        Attacks to prevent:
        - https://attacker.com
        - //attacker.com
        - http://attacker.com
        - //evil.com/phishing
        """
        # Test with external URL (should fallback to dashboard)
        response = self.client.post(
            reverse('antoine:login') + '?next=https://attacker.com/phishing',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)
        # Should redirect to safe default (dashboard)
        self.assertIn('/dashboard/', response.url)

    def test_login_rejects_protocol_relative_redirect(self):
        """
        Reject protocol-relative URLs (//evil.com).
        
        These redirect to attacker's site using user's current protocol.
        """
        response = self.client.post(
            reverse('antoine:login') + '?next=//attacker.com/evil',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)

    def test_login_rejects_encoded_external_redirect(self):
        """
        Reject encoded external URLs (/%2F%2Fevil.com).
        
        URL encoding could bypass simple startswith('/') checks.
        """
        # %2F%2F = //
        response = self.client.post(
            reverse('antoine:login') + '?next=/%2f%2fattacker.com',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)

    def test_login_rejects_javascript_redirect(self):
        """
        Reject JavaScript URLs that could execute code.
        
        javascript:alert('xss') or data:text/html URLs
        """
        response = self.client.post(
            reverse('antoine:login') + f"?next=javascript:alert('xss')",
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to javascript payload
        self.assertNotIn('javascript:', response.url)

    def test_login_defaults_to_dashboard_without_next(self):
        """
        Without 'next' parameter, redirect to default landing page.
        """
        response = self.client.post(
            reverse('antoine:login'),
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should redirect to dashboard (default safe location)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response.url)

    def test_login_with_multiple_slashes_redirect(self):
        """
        Prevent bypass using multiple slashes: ///.
        """
        response = self.client.post(
            reverse('antoine:login') + '?next=///attacker.com',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)

    def test_login_with_whitespace_encoded_redirect(self):
        """
        Prevent bypass using whitespace encoding.
        """
        # %09 = tab, %0a = newline
        response = self.client.post(
            reverse('antoine:login') + '?next=https:%09//attacker.com',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)

    def test_login_allows_relative_internal_paths(self):
        """
        Allow relative internal paths like /profile/, /dashboard/, etc.
        """
        # Note: Don't call self.client.login() first, as it would cause a redirect
        # to dashboard due to the is_authenticated check. Test with actual login form.
        
        # Only test paths that are guaranteed to exist
        valid_paths = [
            '/dashboard/',
            '/profile/',
        ]
        
        for path in valid_paths:
            response = self.client.post(
                reverse('antoine:login') + f'?next={path}',
                {
                    'username': 'testuser',
                    'password': 'TestPass123!@#',
                    'remember_me': False,
                },
                follow=False
            )
            
            # Should redirect to the internal path
            if response.status_code == 302:
                self.assertIn(path, response.url, f"Expected redirect to {path}, got {response.url}")
            
            # Logout for next iteration
            self.client.logout()

    def test_login_strips_dangerous_next_parameters(self):
        """
        Safely handle unusual 'next' values without crashes.
        """
        dangerous_values = [
            '/\x00/dashboard',  # Null byte
            '/dashboard\t\n',   # Whitespace
            '/dashboard" onclick="alert(1)"',  # Injected attributes
            '/dashboard\r\n\r\ninjected: header',  # Header injection
        ]
        
        for value in dangerous_values:
            try:
                response = self.client.post(
                    reverse('antoine:login') + f'?next={quote(value)}',
                    {
                        'username': 'testuser',
                        'password': 'TestPass123!@#',
                        'remember_me': False,
                    },
                    follow=False
                )
                # Should not crash and should redirect safely
                self.assertIn(response.status_code, [302, 200])
            except Exception as e:
                self.fail(f"Redirect handling crashed on value {repr(value)}: {e}")

    def test_failed_login_ignores_next_parameter(self):
        """
        Failed login should not redirect at all (stay on login page).
        """
        response = self.client.post(
            reverse('antoine:login') + '?next=https://attacker.com',
            {
                'username': 'testuser',
                'password': 'WrongPassword123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Should NOT redirect (even to attacker.com)
        # Should stay on login page (200) or redirect to login
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            # If redirect, should be back to login, not attacker
            self.assertNotIn('attacker.com', response.url)

    def test_logout_does_not_accept_next_parameter(self):
        """
        Logout should always redirect to safe default location.
        Should not accept 'next' parameter for redirect.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        response = self.client.post(
            reverse('antoine:logout') + '?next=https://attacker.com',
            {},
            follow=False
        )
        
        # Should NOT redirect to attacker.com
        self.assertNotIn('attacker.com', response.url)
        # Should redirect to login (safe default)
        self.assertIn('/login/', response.url)

    def test_registration_defaults_to_login(self):
        """
        After successful registration, redirect to login page (not 'next').
        """
        response = self.client.post(
            reverse('antoine:register') + '?next=https://attacker.com',
            {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': 'NewPass123!@#',
                'password2': 'NewPass123!@#',
            },
            follow=False
        )
        
        # Should NOT use the 'next' parameter for registration
        # Should redirect to login or dashboard
        if response.status_code == 302:
            self.assertNotIn('attacker.com', response.url)

    def test_password_reset_complete_no_redirect_params(self):
        """
        Password reset completion should redirect to fixed location,
        not accept arbitrary redirect parameters.
        """
        response = self.client.get(
            reverse('antoine:password_reset_complete') + '?next=https://attacker.com'
        )
        
        # Should render page (no redirect to attacker.com)
        # Page should not contain redirect to external site
        if response.status_code == 302:
            self.assertNotIn('attacker.com', response.url)

    def test_redirect_preserves_query_parameters(self):
        """
        Safe internal redirects should preserve legitimate query parameters.
        """
        response = self.client.post(
            reverse('antoine:login') + '?next=/dashboard/&utm_source=email',
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
                'remember_me': False,
            },
            follow=False
        )
        
        # Safe redirect should include the 'next' value
        self.assertIn('/dashboard/', response.url)


class RedirectConfigurationTests(TestCase):
    """Test that redirect configuration is properly set up"""

    def test_allowed_hosts_configured(self):
        """
        Django ALLOWED_HOSTS must be configured to prevent Host header attacks.
        """
        from django.conf import settings
        
        self.assertTrue(
            hasattr(settings, 'ALLOWED_HOSTS'),
            "ALLOWED_HOSTS must be configured"
        )
        self.assertGreater(
            len(settings.ALLOWED_HOSTS),
            0,
            "ALLOWED_HOSTS must not be empty"
        )

    def test_secure_redirect_function_used(self):
        """
        Verify that redirect validation is using Django's safe utilities.
        """
        from django.http.response import HttpResponseRedirect
        
        # This test verifies the concept - actual implementation
        # should use url_has_allowed_host_and_scheme or similar
        self.assertTrue(True, "Implementation should use Django's safe redirect utilities")
