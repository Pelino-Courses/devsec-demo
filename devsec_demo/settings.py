"""
Django settings for devsec_demo project.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=None, required=False):
    """Read an environment variable, raising ImproperlyConfigured when required and absent."""
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f"Required environment variable '{name}' is not set. "
            "Add it to your .env file or deployment environment."
        )
    return value


# ── Secret key ────────────────────────────────────────────────────────────────
# Must be set via environment. A blank or missing key is a hard failure because
# Django uses it for signing sessions, CSRF tokens, and password-reset links.
SECRET_KEY = _env('DJANGO_SECRET_KEY', required=True)

# ── Debug mode ────────────────────────────────────────────────────────────────
# Defaults to False. Must never be True in production — it exposes stack traces,
# SQL queries, and settings values to any visitor.
DEBUG = _env('DJANGO_DEBUG', 'False').lower() == 'true'

# ── Allowed hosts ─────────────────────────────────────────────────────────────
# Prevents HTTP Host-header injection. Wildcard '*' is rejected outside DEBUG.
_raw_hosts = _env('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]
if not DEBUG and '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must not contain '*' when DEBUG is False."
    )


# ── Application definition ────────────────────────────────────────────────────

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shema',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'shema.middleware.SecurityAuditMiddleware',
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ── Database ──────────────────────────────────────────────────────────────────

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ── Password validation ───────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Internationalisation ──────────────────────────────────────────────────────

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ── Static / media files ──────────────────────────────────────────────────────

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Hard Django request-body cap (avatar + document forms)
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024  # 6 MB


# ── Security headers ──────────────────────────────────────────────────────────
# X-Content-Type-Options: nosniff — prevents MIME-type sniffing attacks.
SECURE_CONTENT_TYPE_NOSNIFF = True

# X-Frame-Options: DENY — prevents clickjacking via iframes.
X_FRAME_OPTIONS = 'DENY'

# Referrer-Policy: same-origin — hides the Referer header on cross-origin requests,
# reducing information leakage without breaking same-site navigation.
SECURE_REFERRER_POLICY = 'same-origin'


# ── Cookie security ───────────────────────────────────────────────────────────
# HttpOnly: prevents JavaScript from reading the session cookie,
# which limits the impact of XSS attacks that try to steal sessions.
SESSION_COOKIE_HTTPONLY = True

# SameSite=Lax: cookies are sent on same-site requests and safe top-level
# cross-site navigations (GET), but not on cross-origin POST — blocking CSRF.
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Session lifetime: expire after 2 hours of inactivity and always on
# browser close, limiting the window for session hijacking.
SESSION_COOKIE_AGE = 7200            # 2 hours in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF_COOKIE_HTTPONLY must remain False: Django's JS client reads this
# cookie to attach the token to AJAX requests. Setting it True would
# break all AJAX forms.
CSRF_COOKIE_HTTPONLY = False


# ── Transport security (HTTPS) ────────────────────────────────────────────────
# Controlled by DJANGO_HTTPS env var so local HTTP development still works.
# In production set DJANGO_HTTPS=true alongside a valid TLS certificate.
DJANGO_HTTPS = _env('DJANGO_HTTPS', 'False').lower() == 'true'

if DJANGO_HTTPS:
    # Force all HTTP requests to HTTPS.
    SECURE_SSL_REDIRECT = True
    # Mark cookies as Secure so they are never sent over plain HTTP.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: instruct browsers to only contact this site over HTTPS for 1 year.
    # Include subdomains and request preloading for maximum protection.
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Tell Django the request is HTTPS when behind a reverse proxy.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in _env(
        'CSRF_TRUSTED_ORIGINS',
        'http://localhost:8000,http://127.0.0.1:8000',
    ).split(',')
    if o.strip()
]


# ── Logging ───────────────────────────────────────────────────────────────────

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'security.log',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


# ── Authentication ────────────────────────────────────────────────────────────

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
