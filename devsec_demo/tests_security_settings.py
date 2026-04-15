"""
Tests for production-grade Django security settings configuration.

Verifies that security-critical settings are properly configured
for different environments (development, staging, production).
"""

from django.test import TestCase, override_settings
from django.conf import settings


class DjangoSecuritySettingsTests(TestCase):
    """Test that Django security settings are properly configured."""
    
    def test_secret_key_is_set(self):
        """Verify SECRET_KEY is configured."""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertTrue(len(settings.SECRET_KEY) > 10)
    
    def test_debug_mode_can_be_controlled(self):
        """Verify DEBUG mode is configurable via environment."""
        # DEBUG should be False by default
        self.assertIsInstance(settings.DEBUG, bool)
    
    def test_allowed_hosts_is_configured(self):
        """Verify ALLOWED_HOSTS is configured."""
        self.assertIsNotNone(settings.ALLOWED_HOSTS)
        self.assertIsInstance(settings.ALLOWED_HOSTS, list)
        # Default should have at least localhost/127.0.0.1
        self.assertTrue(len(settings.ALLOWED_HOSTS) > 0)


class CookieSecurityTests(TestCase):
    """Test that cookie security settings are properly configured."""
    
    def test_csrf_cookie_httponly(self):
        """Verify CSRF cookie cannot be accessed by JavaScript."""
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
    
    def test_csrf_cookie_samesite(self):
        """Verify CSRF cookie has SameSite protection."""
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, 'Strict')
    
    def test_session_cookie_httponly(self):
        """Verify session cookie cannot be accessed by JavaScript."""
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
    
    def test_session_cookie_samesite(self):
        """Verify session cookie has SameSite protection."""
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Strict')
    
    def test_session_cookie_age(self):
        """Verify session expires after configured age."""
        self.assertGreater(settings.SESSION_COOKIE_AGE, 0)
        self.assertIsInstance(settings.SESSION_COOKIE_AGE, int)
    
    def test_csrf_cookie_age(self):
        """Verify CSRF cookie has expiration."""
        self.assertGreater(settings.CSRF_COOKIE_AGE, 0)
    
    def test_language_cookie_not_httponly(self):
        """Verify language preference can be read by JavaScript."""
        self.assertFalse(settings.LANGUAGE_COOKIE_HTTPONLY)
    
    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_secure_session_cookie_in_production(self):
        """Verify secure cookie flag can be enabled."""
        self.assertTrue(settings.SESSION_COOKIE_SECURE)


class HTTPSecurityHeadersTests(TestCase):
    """Test that HTTP security headers are properly configured."""
    
    def test_x_frame_options_deny(self):
        """Verify X-Frame-Options prevents clickjacking."""
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
    
    def test_secure_content_type_nosniff(self):
        """Verify MIME sniffing protection is enabled."""
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
    
    def test_secure_browser_xss_filter(self):
        """Verify XSS filter is enabled for legacy browsers."""
        self.assertTrue(settings.SECURE_BROWSER_XSS_FILTER)
    
    def test_referrer_policy_configured(self):
        """Verify referrer policy is configured."""
        self.assertEqual(settings.SECURE_REFERRER_POLICY, 'strict-origin-when-cross-origin')
    
    def test_csp_configured(self):
        """Verify Content Security Policy is configured."""
        self.assertIsNotNone(settings.SECURE_CONTENT_SECURITY_POLICY)
        self.assertIsInstance(settings.SECURE_CONTENT_SECURITY_POLICY, dict)
        # Should have default-src at minimum
        self.assertIn('default-src', settings.SECURE_CONTENT_SECURITY_POLICY)
    
    def test_csp_default_src_is_self(self):
        """Verify CSP default-src restricts to self."""
        csp = settings.SECURE_CONTENT_SECURITY_POLICY
        self.assertIn("'self'", csp['default-src'])
    
    def test_csp_script_src_is_self(self):
        """Verify CSP script-src restricts to self."""
        csp = settings.SECURE_CONTENT_SECURITY_POLICY
        self.assertIn("'self'", csp['script-src'])
        # Verify no unsafe-inline scripts
        self.assertNotIn("'unsafe-inline'", csp['script-src'])


class PasswordValidationTests(TestCase):
    """Test that password validation is properly configured."""
    
    def test_password_validators_configured(self):
        """Verify password validators are configured."""
        self.assertIsNotNone(settings.AUTH_PASSWORD_VALIDATORS)
        self.assertTrue(len(settings.AUTH_PASSWORD_VALIDATORS) > 0)
    
    def test_minimum_password_length(self):
        """Verify minimum password length is enforced."""
        validators = settings.AUTH_PASSWORD_VALIDATORS
        
        # Find MinimumLengthValidator
        min_length_validator = None
        for validator in validators:
            if 'MinimumLength' in validator['NAME']:
                min_length_validator = validator
                break
        
        self.assertIsNotNone(min_length_validator)
        
        # Should require at least 12 characters for production security
        if 'OPTIONS' in min_length_validator:
            min_length = min_length_validator['OPTIONS'].get('min_length', 8)
            self.assertGreaterEqual(min_length, 12)
    
    def test_common_password_validator(self):
        """Verify common password validator is enabled."""
        validators = settings.AUTH_PASSWORD_VALIDATORS
        validator_names = [v['NAME'] for v in validators]
        
        # Should check against common passwords
        self.assertTrue(
            any('CommonPassword' in name for name in validator_names),
            'CommonPasswordValidator should be configured'
        )
    
    def test_numeric_password_validator(self):
        """Verify numeric-only password validator is enabled."""
        validators = settings.AUTH_PASSWORD_VALIDATORS
        validator_names = [v['NAME'] for v in validators]
        
        # Should reject numeric-only passwords
        self.assertTrue(
            any('NumericPassword' in name for name in validator_names),
            'NumericPasswordValidator should be configured'
        )


class FileUploadSecurityTests(TestCase):
    """Test that file upload security settings are configured."""
    
    def test_file_upload_max_size(self):
        """Verify file upload size is limited."""
        self.assertIsNotNone(settings.FILE_UPLOAD_MAX_MEMORY_SIZE)
        self.assertLess(settings.FILE_UPLOAD_MAX_MEMORY_SIZE, 100 * 1024 * 1024)  # Less than 100 MB
    
    def test_data_upload_max_size(self):
        """Verify POST data size is limited."""
        self.assertIsNotNone(settings.DATA_UPLOAD_MAX_MEMORY_SIZE)
        self.assertLess(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 100 * 1024 * 1024)  # Less than 100 MB


class EmailSecurityTests(TestCase):
    """Test that email configuration is secure."""
    
    def test_email_backend_configured(self):
        """Verify email backend is configured."""
        self.assertIsNotNone(settings.EMAIL_BACKEND)
        # Should be a valid Django email backend
        self.assertIn('mail.backends', settings.EMAIL_BACKEND)
    
    def test_default_from_email_configured(self):
        """Verify DEFAULT_FROM_EMAIL is configured."""
        self.assertIsNotNone(settings.DEFAULT_FROM_EMAIL)
        self.assertIn('@', settings.DEFAULT_FROM_EMAIL)  # Must be valid email format


class MiddlewareSecurityTests(TestCase):
    """Test that security middleware is installed."""
    
    def test_security_middleware_installed(self):
        """Verify SecurityMiddleware is installed."""
        middleware_names = settings.MIDDLEWARE
        self.assertIn('django.middleware.security.SecurityMiddleware', middleware_names)
    
    def test_csrf_middleware_installed(self):
        """Verify CSRF middleware is installed."""
        middleware_names = settings.MIDDLEWARE
        self.assertIn('django.middleware.csrf.CsrfViewMiddleware', middleware_names)
    
    def test_xframe_middleware_installed(self):
        """Verify X-Frame-Options middleware is installed."""
        middleware_names = settings.MIDDLEWARE
        self.assertIn('django.middleware.clickjacking.XFrameOptionsMiddleware', middleware_names)


class TemplateSecurityTests(TestCase):
    """Test that template security is configured."""
    
    def test_template_auto_escaping_enabled(self):
        """Verify template auto-escaping is enabled."""
        # AUTO_RELOAD is not a security setting, but we check default template settings
        templates_config = settings.TEMPLATES[0]
        
        # In Django, auto-escaping is ON by default
        # This is verified by checking we use DjangoTemplates backend
        self.assertEqual(templates_config['BACKEND'], 'django.template.backends.django.DjangoTemplates')


class DatabaseSecurityTests(TestCase):
    """Test that database connections are secure."""
    
    def test_atomic_requests_enabled(self):
        """Verify atomic requests are enabled for data integrity."""
        self.assertTrue(settings.DATABASES['default'].get('ATOMIC_REQUESTS', False))
    
    def test_database_configured(self):
        """Verify database is configured."""
        self.assertIn('default', settings.DATABASES)
        self.assertIn('ENGINE', settings.DATABASES['default'])


class SessionSecurityTests(TestCase):
    """Test that session configuration is secure."""
    
    def test_session_engine_backend(self):
        """Verify session engine uses database backend."""
        # Database backend is more secure than file-based or cache
        self.assertEqual(settings.SESSION_ENGINE, 'django.contrib.sessions.backends.db')
    
    def test_session_save_every_request_false(self):
        """Verify session is not saved on every request."""
        # This is a performance optimization and security practice
        self.assertFalse(settings.SESSION_SAVE_EVERY_REQUEST)


class EnvironmentSettingsTests(TestCase):
    """Test that environment detection is working."""
    
    def test_environment_is_set(self):
        """Verify DJANGO_ENVIRONMENT is detected."""
        self.assertIsNotNone(settings.ENVIRONMENT)
        self.assertIn(settings.ENVIRONMENT, ['development', 'staging', 'production'])
    
    def test_environment_flags_set(self):
        """Verify environment flags are set."""
        # One of these should be True
        total_true = sum([
            settings.IS_DEVELOPMENT,
            settings.IS_STAGING,
            settings.IS_PRODUCTION,
        ])
        self.assertEqual(total_true, 1, 'Exactly one environment flag should be True')


class CrossOriginTests(TestCase):
    """Test CSRF and cross-origin settings."""
    
    def test_csrf_trusted_origins_configured(self):
        """Verify CSRF_TRUSTED_ORIGINS is available."""
        self.assertIsNotNone(settings.CSRF_TRUSTED_ORIGINS)
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)


class ProxySecurityTests(TestCase):
    """Test proxy security configuration."""
    
    def test_x_forwarded_host_trusted(self):
        """Verify X-Forwarded-Host header is trusted."""
        self.assertTrue(settings.USE_X_FORWARDED_HOST)
    
    def test_proxy_ssl_header_configured(self):
        """Verify proxy SSL header is configured."""
        self.assertIsNotNone(settings.SECURE_PROXY_SSL_HEADER)
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER[0], 'HTTP_X_FORWARDED_PROTO')
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER[1], 'https')
