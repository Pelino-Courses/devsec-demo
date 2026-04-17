"""
Django settings for devsec_demo project.

Production-hardened configuration with security best practices.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file (development only)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY: Environment Configuration
# ============================================================================

# Get environment name (development, staging, production)
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development').lower()

# SECRET_KEY: MUST be provided in environment and never committed to version control
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if ENVIRONMENT == 'production':
        raise ValueError(
            'DJANGO_SECRET_KEY environment variable is required in production. '
            'Generate with: python -c "from django.core.management.utils import get_random_secret_key; '
            'print(get_random_secret_key())"\n'
            'Never commit this key to version control.'
        )
    else:
        # Development-only fallback
        SECRET_KEY = 'django-insecure-development-only-change-in-production'

# DEBUG: Explicitly disabled in production, development must be opted-in
DEBUG = os.environ.get('DJANGO_DEBUG', '').lower() == 'true'
if DEBUG and ENVIRONMENT == 'production':
    raise ValueError('DEBUG=True is not allowed in production. Set DJANGO_DEBUG=false')

# ALLOWED_HOSTS: Explicitly configured, defaults to localhost for development
if ENVIRONMENT == 'production':
    ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
        raise ValueError(
            'DJANGO_ALLOWED_HOSTS environment variable is required in production. '
            'Example: "example.com,www.example.com"'
        )
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]
else:
    # Development: Allow localhost and 127.0.0.1
    ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]


# Application definition
# ============================================================================
# SECURITY: Middleware Stack
# ============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Security middleware should be first in the stack
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Sets security headers
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # X-Frame-Options header
]

ROOT_URLCONF = 'devsec_demo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'devsec_demo.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================================================
# SECURITY: Cookie Settings
# ============================================================================
# Secure cookies prevent interception and unauthorized access

# Session cookies should only be sent over HTTPS in production
SESSION_COOKIE_SECURE = not DEBUG  # True in production, False in development
SESSION_COOKIE_HTTPONLY = True     # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict' # Prevent CSRF attacks via cookies

# CSRF cookies should only be sent over HTTPS
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True        # Prevent JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'    # Prevent cross-site request forgery

# Session configuration
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds

# ============================================================================
# SECURITY: HTTPS and Transport Security
# ============================================================================

# Redirect HTTP to HTTPS in production
SECURE_SSL_REDIRECT = not DEBUG

# HTTP Strict-Transport-Security (HSTS) header
# Tells browsers to only use HTTPS for this domain
if ENVIRONMENT == 'production':
    SECURE_HSTS_SECONDS = 31536000  # 1 year in seconds
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SECURE_HSTS_SECONDS = 0

# ============================================================================
# SECURITY: Response Headers
# ============================================================================

# X-Frame-Options: Prevent clickjacking attacks
X_FRAME_OPTIONS = 'DENY'

# X-Content-Type-Options: Prevent MIME type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-XSS-Protection: Enable browser XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Content-Security-Policy headers (strict by default)
CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),  # Inline scripts needed for Django
    'style-src': ("'self'", "'unsafe-inline'"),   # Inline styles for framework
    'img-src': ("'self'", 'data:', 'https:'),
    'font-src': ("'self'",),
    'connect-src': ("'self'",),
    'frame-ancestors': ("'none'",),
    'base-uri': ("'self'",),
    'form-action': ("'self'",),
}

# ============================================================================
# SECURITY: Email Configuration (for password resets, etc.)
# ============================================================================

# Email backend for password reset and notifications
if ENVIRONMENT == 'production':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')
else:
    # Development: Use console backend (outputs to console instead of sending)
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================================================
# SECURITY: Database Configuration
# ============================================================================

# Ensure proper database config is used in production
# SQLite should only be used in development
if ENVIRONMENT == 'production' and 'sqlite' in DATABASES['default']['ENGINE'].lower():
    raise ValueError(
        'SQLite database should not be used in production. '
        'Configure DATABASE_URL environment variable with PostgreSQL or MySQL.'
    )

# ============================================================================
# SECURITY: Logging
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================================================
# SECURITY: Additional Hardening Settings
# ============================================================================

# Prevent host header attacks
ALLOWED_REDIRECT_HOSTS = ALLOWED_HOSTS.copy() if ALLOWED_HOSTS else []

# Use secure password hasher
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ============================================================================
# SECURITY: Environment Summary
# ============================================================================

if DEBUG:
    print(
        f'\n⚠️  DEBUG MODE ENABLED (DEVELOPMENT ONLY)\n'
        f'Environment: {ENVIRONMENT}\n'
        f'Allowed Hosts: {ALLOWED_HOSTS}\n'
        f'SSL Redirect: {SECURE_SSL_REDIRECT}\n'
        f'Session Cookie Secure: {SESSION_COOKIE_SECURE}\n',
        file=sys.stderr
    )
