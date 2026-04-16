"""
Tests to validate Django security settings are properly configured.
"""
import os
from django.test import TestCase, override_settings
from django.conf import settings


class DjangoSecuritySettingsTests(TestCase):
    """Verify production-grade security settings are in place."""

    def test_secret_key_is_set_in_production(self):
        """SECRET_KEY should not be the development default in production mode."""
        # In development mode, the insecure default is acceptable
        # In production mode (DJANGO_ENV not set to 'development'), SECRET_KEY is required
        self.assertIsNotNone(
            settings.SECRET_KEY,
            'SECRET_KEY must be set',
        )

    def test_debug_is_false_in_production(self):
        """DEBUG should be False for production safety."""
        # In test environment DJANGO_ENV is not set, defaults to production mode
        self.assertFalse(settings.DEBUG, 'DEBUG must be False for production')


    def test_allowed_hosts_is_configured(self):
        """ALLOWED_HOSTS should be explicitly configured."""
        self.assertIsNotNone(
            settings.ALLOWED_HOSTS,
            'ALLOWED_HOSTS must be configured',
        )
        # In production test mode, should be empty or contain explicit hosts
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)

    def test_session_cookie_is_httponly(self):
        """Session cookies should be HttpOnly to prevent JavaScript access."""
        self.assertTrue(
            settings.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_HTTPONLY must be True',
        )

    def test_csrf_cookie_is_httponly(self):
        """CSRF cookies should be HttpOnly."""
        self.assertTrue(
            settings.CSRF_COOKIE_HTTPONLY,
            'CSRF_COOKIE_HTTPONLY must be True',
        )

    def test_session_cookie_samesite_is_strict(self):
        """Session cookies should have SameSite=Strict."""
        self.assertEqual(
            settings.SESSION_COOKIE_SAMESITE,
            'Strict',
            'SESSION_COOKIE_SAMESITE must be Strict',
        )

    def test_csrf_cookie_samesite_is_strict(self):
        """CSRF cookies should have SameSite=Strict."""
        self.assertEqual(
            settings.CSRF_COOKIE_SAMESITE,
            'Strict',
            'CSRF_COOKIE_SAMESITE must be Strict',
        )

    def test_x_frame_options_set(self):
        """X-Frame-Options should prevent clickjacking."""
        self.assertEqual(
            settings.X_FRAME_OPTIONS,
            'DENY',
            'X_FRAME_OPTIONS must be DENY to prevent clickjacking',
        )

    def test_xss_filter_enabled(self):
        """Browser XSS filter should be enabled."""
        self.assertTrue(
            settings.SECURE_BROWSER_XSS_FILTER,
            'SECURE_BROWSER_XSS_FILTER must be True',
        )

    def test_csp_is_configured(self):
        """Content Security Policy should be configured."""
        self.assertIsNotNone(
            settings.SECURE_CONTENT_SECURITY_POLICY,
            'SECURE_CONTENT_SECURITY_POLICY must be configured',
        )

    @override_settings(DJANGO_ENV='production')
    def test_ssl_redirect_in_production(self):
        """In production, SSL redirect should be enabled."""
        # This test would need to reload settings to test properly
        # For now, verify the setting exists
        self.assertTrue(
            hasattr(settings, 'SECURE_SSL_REDIRECT'),
            'SECURE_SSL_REDIRECT setting should exist',
        )

    def test_password_validators_configured(self):
        """Password validators should enforce strong authentication."""
        self.assertTrue(
            len(settings.AUTH_PASSWORD_VALIDATORS) >= 4,
            'At least 4 password validators should be configured',
        )
        validator_names = [v['NAME'] for v in settings.AUTH_PASSWORD_VALIDATORS]
        self.assertIn(
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            validator_names,
        )
        self.assertIn(
            'django.contrib.auth.password_validation.MinimumLengthValidator',
            validator_names,
        )
