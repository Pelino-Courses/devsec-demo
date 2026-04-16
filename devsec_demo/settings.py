"""
Django settings for devsec_demo project.

Security settings are environment-driven. Required environment variables:
  DJANGO_SECRET_KEY  - cryptographic secret, must be set in all environments
  DJANGO_DEBUG       - set to 'True' only in local development, never in production
  DJANGO_ALLOWED_HOSTS - comma-separated list of allowed hostnames
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Security-critical settings
# ---------------------------------------------------------------------------

# SECRET_KEY must always be set explicitly. We raise an error at startup
# rather than running with None, which would silently break all
# cryptographic signing (sessions, CSRF tokens, password reset links).
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError(
        'DJANGO_SECRET_KEY environment variable is not set. '
        'Set it in your .env file or deployment environment.'
    )

# DEBUG must be an explicit boolean. os.environ.get returns a string, so
# "False" would be truthy if not converted. We compare explicitly to "True"
# so any other value (including missing) defaults to False.
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# ALLOWED_HOSTS must be explicit. An empty list means Django rejects all
# requests in production. We read from the environment so this can differ
# between development and production without code changes.
_allowed_hosts_env = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'eduard',
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


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MAX_UPLOAD_SIZE = 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# Cookie security
# ---------------------------------------------------------------------------

# SESSION_COOKIE_HTTPONLY prevents JavaScript from reading the session
# cookie. This is True by default in Django but we set it explicitly
# so the intent is clear and auditable.
SESSION_COOKIE_HTTPONLY = True

# CSRF_COOKIE_HTTPONLY prevents JavaScript from reading the CSRF cookie.
# Note: our AJAX views read the CSRF token from the cookie using JS, so
# this must remain False to allow the X-CSRFToken header pattern to work.
CSRF_COOKIE_HTTPONLY = False

# SameSite=Lax prevents the session cookie from being sent on
# cross-site requests (e.g. a link from another site), which provides
# CSRF protection at the browser level in addition to Django's token check.
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Secure cookie flags should be True in production (HTTPS only).
# We tie these to DEBUG so they are False in local development
# (which runs on HTTP) and True in production (which must use HTTPS).
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'
CSRF_COOKIE_SECURE = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'


# ---------------------------------------------------------------------------
# Transport and browser security headers
# ---------------------------------------------------------------------------

# Tell browsers not to sniff the content type of responses. Prevents a
# browser from treating a text file as executable HTML or JavaScript.
SECURE_CONTENT_TYPE_NOSNIFF = True

# Prevent the site from being embedded in an iframe on another origin.
# This mitigates clickjacking attacks. DENY is stricter than SAMEORIGIN.
X_FRAME_OPTIONS = 'DENY'

# In production (DEBUG=False), redirect all HTTP requests to HTTPS.
# Disabled in development because runserver does not support HTTPS.
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'

# Once a browser has visited over HTTPS, HSTS tells it to only use HTTPS
# for future visits for the specified duration (1 year = 31536000 seconds).
# Only active when DEBUG is False to avoid breaking local development.
SECURE_HSTS_SECONDS = 31536000 if os.environ.get('DJANGO_SSL_REDIRECT') == 'True' else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_PRELOAD = os.environ.get('DJANGO_SSL_REDIRECT', 'False') == 'True'


# ---------------------------------------------------------------------------
# Authentication redirects
# ---------------------------------------------------------------------------

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

# Email configuration
# In development with no email credentials set, falls back to console backend
# so emails print to terminal. In production, set EMAIL_HOST_USER and
# EMAIL_HOST_PASSWORD environment variables to send real emails via Gmail.
_email_user = os.environ.get('EMAIL_HOST_USER')
_email_password = os.environ.get('EMAIL_HOST_PASSWORD')

if _email_user and _email_password:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = _email_user
    EMAIL_HOST_PASSWORD = _email_password
    DEFAULT_FROM_EMAIL = _email_user
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
PASSWORD_RESET_TIMEOUT = 86400


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'audit': {
            'format': '[{asctime}] AUDIT {levelname} {name} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'audit',
        },
    },
    'loggers': {
        'eduard.audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}