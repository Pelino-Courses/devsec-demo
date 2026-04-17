# devsec-demo

## Django security learning repository

This repository is used for Django and web security assignments. You will work
from your own fork, complete the assignment linked in GitHub issues, and submit
your work through a pull request.

## How to start an assignment

1. Open the assignment issue you were given.
2. Read the full task carefully.
3. Find the `## Required submission branch` section in the issue.
4. Fork the repository if you have not already done so.
5. Create your working branch from the required `assignment/...` branch named in the issue.

## Submission workflow

- Each assignment issue declares one required submission branch.
- Your pull request must target that exact branch.
- Link exactly one assignment issue in the `Related Issue` section of your pull request.
- Fill in the full pull request template, including:
  - target assignment branch
  - design note
  - security impact
  - validation
  - AI disclosure
  - authorship affirmation
- Your pull request is treated as your submission record for review and grading.
  - Assignment pull requests are expected to pass submission hygiene, lint, and Django health checks.

## AI and authorship policy

This course does not rely on AI detectors as proof. Instead, you are expected
to submit work you understand and can explain.

You may use AI in limited ways such as:

- asking for explanations of Django or security concepts
- getting debugging hints
- looking up documentation or examples
- refining wording or reorganizing code they already understand

You may not:

- delegate the entire assignment to an AI system
- submit code they cannot explain line by line when asked
- copy AI-generated output without reviewing, adapting, and understanding it
- misrepresent AI-authored work as fully their own

You must be able to explain:

- why you chose your implementation approach
- where security controls are enforced
- how you validated the work
- what you changed yourself after any AI assistance

Read [docs/ai-authorship-policy.md](docs/ai-authorship-policy.md) before you
start work on your submission.

---
# S-Auth — DevSec Demo

> **Assignment**: Security Essentials · Django Authentication Service
> **Author**: shema

---

## Overview

S-Auth is a battle-hardened Django authentication service built to demonstrate
real-world security best practices. It implements a full User Authentication
lifecycle — registration, login, password rotation, and logout — layered on top
of Django's built-in `auth` framework, with additional security hardening applied
at every level of the stack.

---

## Security Audit & Hardening

This section documents every security measure applied to the project as part of
the "Security Essentials" assignment.

### 1. HTTP Security Headers (`settings.py`)

| Header | Setting | Value |
|--------|---------|-------|
| XSS Filter | `SECURE_BROWSER_XSS_FILTER` | `True` |
| Content-Type Sniffing | `SECURE_CONTENT_TYPE_NOSNIFF` | `True` |
| Clickjacking Protection | `X_FRAME_OPTIONS` | `DENY` |
| HSTS Duration | `SECURE_HSTS_SECONDS` | `31536000` (1 year) |
| HSTS Subdomains | `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` |
| HSTS Preload | `SECURE_HSTS_PRELOAD` | `True` |

All HTTPS/HSTS settings are **toggled via `.env`** using `DJANGO_SECURE_COOKIES=True`
so they default to safe values in staging/production without breaking local HTTP development.

### 2. Secure Cookie Configuration

| Cookie Setting | Value (Production) |
|---------------|--------------------|
| `SESSION_COOKIE_SECURE` | `True` |
| `CSRF_COOKIE_SECURE` | `True` |
| `SECURE_SSL_REDIRECT` | `True` |

Controlled by the `DJANGO_SECURE_COOKIES` environment variable in `.env`.

### 3. CSRF Protection

- All forms include `{% csrf_token %}`.
- `CSRF_TRUSTED_ORIGINS` is configurable via `.env` — prevents host-header injection.
- Django's `CsrfViewMiddleware` is active in the middleware stack.

### 4. Security Audit Middleware (`shema/middleware.py`)

A custom `SecurityAuditMiddleware` and Django signal receivers log all
authentication events to `security.log`:

```
INFO  2026-04-15 ... SUCCESSFUL_LOGIN: User 'alice' logged in from IP 192.168.1.5
WARNING 2026-04-15 ... FAILED_LOGIN: Attempt for user 'alice' from IP 192.168.1.5
INFO  2026-04-15 ... NEW_USER_REGISTERED: 'bob' from IP 127.0.0.1
```

Events captured:
- ✅ Successful logins (IP + username)
- ⚠️ Failed login attempts (username tried + IP — brute-force detection basis)
- ✅ New user registrations (IP + username)

### 5. Safe Redirect Handling (`shema/views.py`)

The login view uses Django's `url_has_allowed_host_and_scheme()` to validate
the `?next=` redirect parameter, preventing **open redirect attacks**.

### 6. Password Security

- Uses Django's built-in `PBKDF2-SHA256` password hashing (no plaintext ever stored).
- `PasswordChangeForm` paired with `update_session_auth_hash()` keeps the session
  alive after password rotation without forcing re-login.
- All four Django password validators are enabled:
  - `UserAttributeSimilarityValidator`
  - `MinimumLengthValidator`
  - `CommonPasswordValidator`
  - `NumericPasswordValidator`

### 7. Access Control

- All sensitive views (`/profile/`, `/password-change/`) are protected by
  `@login_required`, which redirects unauthenticated users to `/login/`.

---

## Technical Implementation

- **Framework**: Django 6.x
- **App Name**: `shema`
- **Config**: All secrets and toggle flags managed via `.env` (loaded by `python-dotenv`)
- **Styling**: Custom glassmorphic design system (vanilla CSS) + Bootstrap 5 grid

### Project Structure

```
devsec-demo/
├── devsec_demo/
│   ├── settings.py        # Hardened settings with env-controlled security flags
│   └── urls.py
├── shema/
│   ├── middleware.py      # SecurityAuditMiddleware + signal receivers
│   ├── views.py           # Auth views with safe redirects and audit logging
│   ├── tests.py           # Unit tests for all authentication flows
│   ├── templates/shema/   # Premium glassmorphic UI templates
│   └── static/shema/css/  # Full design system (main.css)
├── .env                   # Environment variables (not committed to VCS)
├── security.log           # Runtime audit log (auto-created)
└── README.md
```

---

## Setup & Usage

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate     # Windows
source venv/bin/activate    # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
# Edit .env — set DJANGO_SECRET_KEY, DJANGO_DEBUG, etc.

# 4. Apply migrations
python manage.py migrate

# 5. Run development server
python manage.py runserver
```

### URL Routes

| Path | View | Auth Required |
|------|------|---------------|
| `/` | Home | No |
| `/register/` | Registration | No |
| `/login/` | Login | No |
| `/logout/` | Logout (POST) | Yes |
| `/profile/` | Account Dashboard | ✅ Yes |
| `/password-change/` | Password Rotation | ✅ Yes |

---

## Testing

```bash
# Run all unit tests
python manage.py test shema --verbosity=2

# Run Django's deployment security checklist
python manage.py check --deploy
```

**Test Results**: 5 tests — all passing ✅
- `test_home_page_status_code` — Home page accessible
- `test_login_flow` — Login + redirect works
- `test_logout_flow` — Logout clears session
- `test_profile_protected_access` — Unauthenticated users redirected to login
- `test_registration_flow` — Registration creates user and logs them in

---

## AI Disclosure

This implementation was developed with assistance from **Antigravity** (Google DeepMind's
AI coding assistant). The AI assisted in:

- Security hardening of `settings.py` and middleware design.
- Template generation with the glassmorphic design system.
- Writing unit tests for the authentication workflow.
- Documentation and README drafting.

All security choices, code review, and final logic verification were completed by the student.
