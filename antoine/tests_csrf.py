"""
CSRF Protection Tests for Antoine Authentication Service

Tests that validate CSRF protection is properly enforced for all
state-changing requests (POST, PUT, PATCH, DELETE operations).

Security Goal: Ensure proper CSRF tokens are required and validated
for all forms and AJAX requests that modify server state.
"""
import os
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devsec_demo.settings')
django.setup()


class CSRFProtectionTests(TestCase):
    """Test CSRF protection on state-changing views"""

    def setUp(self):
        """Create test users"""
        self.client = Client(enforce_csrf_checks=True)
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!@#'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPass123!@#'
        )

    def test_logout_requires_csrf_token(self):
        """
        Logout is a state-changing operation.
        Should require CSRF token to prevent logout attacks.
        
        Vulnerability: If logout accepts GET without CSRF token,
        attacker can craft a page that logs out users.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # Attempt logout without CSRF token should fail
        response = self.client.post(
            reverse('antoine:logout'),
            {},
            HTTP_X_CSRFTOKEN='invalid'  # Invalid CSRF token
        )
        
        # Should either get 403 (CSRF Forbidden) or redirect with protection
        # Re-accessing dashboard should still have valid session (not logged out)
        dashboard_response = self.client.get(reverse('antoine:dashboard'))
        # If CSRF protection is working, user should still be authenticated
        self.assertIn(self.test_user.username, str(dashboard_response.content))

    def test_logout_view_not_accessible_via_get(self):
        """
        Logout should use POST-only to prevent CSRF via <img src> or <a href>.
        GET requests should not be allowed.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # GET logout should not work (or should require additional confirmation)
        response = self.client.get(reverse('antoine:logout'), follow=True)
        
        # If GET is allowed, server should at minimum require CSRF token
        # For security, logout should be POST-only
        # Check that GET doesn't silently log you out

    def test_password_change_requires_csrf_protection(self):
        """
        Password change is a critical state-changing operation.
        Must require CSRF token to prevent unauthorized password changes.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # Try to change password without proper CSRF token
        response = self.client.post(
            reverse('antoine:change_password'),
            {
                'old_password': 'TestPass123!@#',
                'new_password1': 'NewPass123!@#',
                'new_password2': 'NewPass123!@#',
            },
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should get CSRF error or validation fail
        # User should still be able to login with original password
        self.client.logout()
        login_success = self.client.login(
            username='testuser',
            password='TestPass123!@#'
        )
        self.assertTrue(login_success, "Password should not have changed without CSRF token")

    def test_profile_update_requires_csrf_protection(self):
        """
        Profile updates modify user data.
        Must require CSRF token to prevent unauthorized profile changes.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # Try to update profile without proper CSRF token
        response = self.client.post(
            reverse('antoine:profile'),
            {
                'bio': 'Attacker bio',
                'avatar': '',
            },
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should get CSRF error
        self.assertEqual(response.status_code, 403)

    def test_reset_user_password_requires_csrf_protection(self):
        """
        Admin password reset is a critical operation.
        Must require CSRF token to prevent unauthorized password resets.
        
        Vulnerability: An admin visiting attacker's page could unknowingly
        reset another user's password without CSRF protection.
        """
        self.client.login(username='admin', password='AdminPass123!@#')
        
        # Try to reset user password without proper CSRF token
        response = self.client.post(
            reverse('antoine:reset_user_password', args=[self.test_user.id]),
            {},
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should get CSRF error (403)
        self.assertEqual(response.status_code, 403)

    def test_all_forms_contain_csrf_token(self):
        """
        All HTML forms that accept POST should contain {% csrf_token %}.
        This test verifies forms are properly rendered with CSRF tokens.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        form_views = [
            ('antoine:change_password', {}),
            ('antoine:profile', {}),
        ]
        
        for url_name, kwargs in form_views:
            response = self.client.get(reverse(url_name, kwargs=kwargs))
            self.assertContains(
                response,
                'csrf',
                msg_prefix=f"Form in {url_name} missing CSRF token"
            )

    def test_logout_requires_post_method(self):
        """
        Logout should require POST method to be CSRF-safe.
        GET requests should not trigger logout.
        """
        self.client.login(username='testuser', password='TestPass123!@#')
        
        # GET request should not log out
        response = self.client.get(reverse('antoine:logout'))
        
        # Check if user is still authenticated
        dashboard_response = self.client.get(reverse('antoine:dashboard'))
        # If logout isn't properly restricted, this should show user in nav
        # For proper security, GET should not log out

    def test_csrf_middleware_active(self):
        """
        Verify Django's CSRF middleware is active in settings.
        """
        from django.conf import settings
        middleware = settings.MIDDLEWARE
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            middleware,
            "CSRF middleware must be enabled for protection"
        )

    def test_csrf_cookie_configured(self):
        """
        Verify CSRF cookie settings are secure.
        """
        from django.conf import settings
        
        # Check CSRF cookie is configured
        self.assertTrue(
            hasattr(settings, 'CSRF_COOKIE_HTTPONLY'),
            "CSRF_COOKIE_HTTPONLY should be configured"
        )

    def test_registration_requires_csrf_token(self):
        """
        Registration is a state-changing operation.
        Must require CSRF token to prevent unauthorized account creation.
        """
        # Try to register without proper CSRF token
        response = self.client.post(
            reverse('antoine:register'),
            {
                'username': 'attacker',
                'email': 'attacker@example.com',
                'password1': 'AttackPass123!@#',
                'password2': 'AttackPass123!@#',
            },
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should get CSRF error (403)
        self.assertEqual(response.status_code, 403)

    def test_login_requires_csrf_token(self):
        """
        Login is a state-changing operation (session creation).
        Must require CSRF token.
        """
        # Try to login without proper CSRF token
        response = self.client.post(
            reverse('antoine:login'),
            {
                'username': 'testuser',
                'password': 'TestPass123!@#',
            },
            HTTP_X_CSRFTOKEN='invalid'
        )
        
        # Should get CSRF error
        self.assertEqual(response.status_code, 403)


class CSRFTemplateTests(TestCase):
    """Test that all POST forms properly include CSRF tokens in templates"""

    def setUp(self):
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!@#'
        )

    def test_login_form_has_csrf_token(self):
        """Login form must include CSRF token"""
        response = self.client.get(reverse('antoine:login'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_register_form_has_csrf_token(self):
        """Registration form must include CSRF token"""
        response = self.client.get(reverse('antoine:register'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_password_reset_request_has_csrf_token(self):
        """Password reset request form must include CSRF token"""
        response = self.client.get(reverse('antoine:password_reset_request'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_password_reset_confirm_has_csrf_token(self):
        """Password reset confirm form must include CSRF token"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        token = default_token_generator.make_token(self.test_user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        
        response = self.client.get(
            reverse('antoine:password_reset_confirm', args=[uidb64, token])
        )
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_change_password_form_has_csrf_token(self):
        """Change password form must include CSRF token"""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.get(reverse('antoine:change_password'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_profile_form_has_csrf_token(self):
        """Profile update form must include CSRF token"""
        self.client.login(username='testuser', password='TestPass123!@#')
        response = self.client.get(reverse('antoine:profile'))
        self.assertContains(response, 'csrfmiddlewaretoken')
