from django.test import TestCase
from django.conf import settings


class SecuritySettingsTest(TestCase):
    """
    Test suite to verify that production-grade security settings are correctly applied.
    """

    def test_debug_is_parsed_as_boolean(self):
        """Verify that DEBUG is a boolean, not a string from environment."""
        self.assertIsInstance(settings.DEBUG, bool)

    def test_secret_key_is_loaded(self):
        """Verify that SECRET_KEY is loaded and not empty."""
        self.assertTrue(len(settings.SECRET_KEY) > 0)
        self.assertNotEqual(settings.SECRET_KEY, 'your-secret-key-here')

    def test_security_headers_configured(self):
        """Verify that various security headers are enabled."""
        self.assertTrue(settings.SECURE_BROWSER_XSS_FILTER)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        self.assertEqual(settings.SECURE_REFERRER_POLICY, 'strict-origin-when-cross-origin')

    def test_cookie_security_settings(self):
        """Verify session and CSRF cookie security settings."""
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Lax')

    def test_allowed_hosts_loaded(self):
        """Verify ALLOWED_HOSTS is loaded and contains at least one entry."""
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        self.assertGreater(len(settings.ALLOWED_HOSTS), 0)

    def test_csrf_trusted_origins_parsing(self):
        """Verify CSRF_TRUSTED_ORIGINS is parsed into a list."""
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)

    def test_https_settings_logic(self):
        """
        Verify HTTPS settings are consistent with the current DEBUG value.
        The invariant: SECURE_SSL_REDIRECT must never be True when DEBUG is True.
        """
        ssl_redirect = getattr(settings, 'SECURE_SSL_REDIRECT', False)
        session_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        csrf_secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)

        if ssl_redirect:
            # If SSL redirect is active, DEBUG must be False
            self.assertFalse(settings.DEBUG,
                "SECURE_SSL_REDIRECT must not be True when DEBUG=True")
        else:
            # SSL redirect is off - correct for development
            # Verify core security settings are still active regardless
            self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
            self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
            self.assertFalse(session_secure)
            self.assertFalse(csrf_secure)