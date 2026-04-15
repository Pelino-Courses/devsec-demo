"""
Django settings for devsec_demo project.

Production-grade security configuration for authentication and authorization system.
See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment detection
ENVIRONMENT = os.environ.get('DJANGO_ENVIRONMENT', 'development').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_STAGING = ENVIRONMENT == 'staging'
IS_DEVELOPMENT = ENVIRONMENT == 'development'


# =============================================================================
# SECRET KEY & SECURITY
# =============================================================================

# Require SECRET_KEY to be explicitly set in all environments
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ValueError(
            'DJANGO_SECRET_KEY must be set in production. '
            'Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
        )
    # Development default (insecure, but safe for local testing)
    SECRET_KEY = 'dev-insecure-key-only-for-local-development-change-in-production'


# Debug mode should never be True in production
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
if DEBUG and IS_PRODUCTION:
    raise ValueError('DEBUG=True is not allowed in production. Set DJANGO_DEBUG=False.')


# =============================================================================
# ALLOWED HOSTS & DOMAIN SETTINGS  
# =============================================================================

# ALLOWED_HOSTS must be explicitly configured
# Do not rely on defaults in production
_allowed_hosts_str = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_str.split(',') if host.strip()]

# Validate ALLOWED_HOSTS in production
if IS_PRODUCTION and (not ALLOWED_HOSTS or ALLOWED_HOSTS == ['localhost', '127.0.0.1']):
    raise ValueError(
        'ALLOWED_HOSTS must be explicitly configured in production. '
        'Set ALLOWED_HOSTS environment variable with your domain(s).'
    )

# CSRF trusted origins for POST requests from cross-origin
CSRF_TRUSTED_ORIGINS = []
if csrf_origins_str := os.environ.get('CSRF_TRUSTED_ORIGINS'):
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins_str.split(',') if origin.strip()]


# =============================================================================
# COOKIE & SESSION SECURITY
# =============================================================================

# CSRF Cookie Security
CSRF_COOKIE_SECURE = IS_PRODUCTION or os.environ.get('CSRF_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF across sites
CSRF_COOKIE_AGE = 31449600  # One year

# Session Cookie Security
SESSION_COOKIE_SECURE = IS_PRODUCTION or os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # Prevent CSRF attacks
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False  # Only save when explicitly modified
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Use SESSION_COOKIE_AGE instead

# Language & Locale Cookie
LANGUAGE_COOKIE_SECURE = IS_PRODUCTION or os.environ.get('LANGUAGE_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
LANGUAGE_COOKIE_HTTPONLY = False  # JavaScript can read language preference
LANGUAGE_COOKIE_SAMESITE = 'Lax'  # Allow navigation cross-site


# =============================================================================
# HTTPS & SECURITY HEADERS
# =============================================================================

# HTTPS enforcement
SECURE_SSL_REDIRECT = IS_PRODUCTION or os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1', 'yes')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Trust headers from reverse proxy

# HTTP Strict Transport Security (HSTS)
# Tells browsers to only connect via HTTPS for the specified duration
SECURE_HSTS_SECONDS = 31536000 if IS_PRODUCTION else 0  # 1 year in production, 0 in dev
SECURE_HSTS_INCLUDE_SUBDOMAINS = IS_PRODUCTION
SECURE_HSTS_PRELOAD = IS_PRODUCTION  # Allow browser to preload HSTS

# X-Frame-Options: Prevent clickjacking
X_FRAME_OPTIONS = 'DENY'

# X-Content-Type-Options: Prevent MIME sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-XSS-Protection: Legacy XSS protection for older browsers
SECURE_BROWSER_XSS_FILTER = True

# Referrer-Policy: Control referrer information
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'


# =============================================================================
# CONTENT SECURITY POLICY
# =============================================================================

# Content Security Policy - Restricts resource loading
# Mitigates XSS and injection attacks
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'",),  # Only scripts from same origin
    'style-src': ("'self'", "'unsafe-inline'"),  # Allow inline styles (needed for Bootstrap)
    'img-src': ("'self'", 'data:', 'https:'),  # Allow images from self and https
    'font-src': ("'self'",),  # Only fonts from same origin
    'connect-src': ("'self'",),  # XHR/fetch only to same origin
    'frame-ancestors': ("'none'",),  # Prevent embedding in iframes
    'base-uri': ("'self'",),  # Restrict base tag
    'form-action': ("'self'",),  # Restrict form submissions
}

# Report CSP violations (optional, for monitoring)
CSP_REPORT_ONLY = not IS_PRODUCTION  # Report mode in dev, enforce in prod


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'antoine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'devsec_demo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'antoine' / 'templates'],
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



# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email configuration - Use environment variables for credentials
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if IS_DEVELOPMENT 
    else 'django.core.mail.backends.smtp.EmailBackend'
)

# SMTP Configuration (only if using SMTP backend)
if 'smtp' in EMAIL_BACKEND.lower():
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    
    if IS_PRODUCTION and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
        raise ValueError(
            'EMAIL_HOST_USER and EMAIL_HOST_PASSWORD must be set in production '
            'when using SMTP email backend.'
        )

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@example.com')

# Login redirect
LOGIN_URL = 'antoine:login'
LOGIN_REDIRECT_URL = 'antoine:dashboard'


# =============================================================================
# ADDITIONAL SECURITY SETTINGS
# =============================================================================

# Password validation - Enforce strong password requirements
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Require at least 12 characters (stronger than default 8)
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Admin URL is randomized in production (optional but recommended)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# Disable unused features
USE_X_FORWARDED_HOST = True  # Trust X-Forwarded-Host header from proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# File upload restrictions
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5 MB

# Prevent directory traversal in file uploads
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
FILE_UPLOAD_TEMP_DIR = None  # Use system temp directory

# Logging - Log security events in production
if IS_PRODUCTION:
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO')
else:
    LOGLEVEL = 'DEBUG'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'standard': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': LOGLEVEL,
            'formatter': 'standard',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'WARNING',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'WARNING',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if IS_PRODUCTION else ['console'],
            'level': LOGLEVEL,
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'] if IS_PRODUCTION else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
logs_dir = BASE_DIR / 'logs'
if IS_PRODUCTION:
    logs_dir.mkdir(exist_ok=True)

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Use database for sessions (secure)

# Prevent session fixation
SESSION_COOKIE_SECURE = IS_PRODUCTION

# Cache configuration (optional, good for performance and security)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Atomic database operations for data integrity
DATABASES['default']['ATOMIC_REQUESTS'] = True

# Persistent database connections in production
if IS_PRODUCTION:
    DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
else:
    DATABASES['default']['CONN_MAX_AGE'] = 0  # No persistence in development


# =============================================================================
# CONFIGURATION SUMMARY (for debugging)
# =============================================================================

if IS_DEVELOPMENT:
    print(f"""
    ✓ Django Security Configuration Loaded
    ✓ Environment: {ENVIRONMENT}
    ✓ Debug: {DEBUG}
    ✓ Allowed Hosts: {ALLOWED_HOSTS}
    ✓ HTTPS Redirect: {SECURE_SSL_REDIRECT}
    ✓ HSTS Enabled: {SECURE_HSTS_SECONDS > 0}
    ✓ CSP Enabled: {bool(SECURE_CONTENT_SECURITY_POLICY)}
    """)
