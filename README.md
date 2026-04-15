# DevSec Demo - Django User Authentication Service

## Project Overview
A complete Django-based User Authentication Service (UAS) demonstrating production-style conventions, secure defaults, and maintainable project structure. This assignment covers the full authentication lifecycle with security best practices.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Authentication Flow](#authentication-flow)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)

---

## Features

### Core Authentication Lifecycle
✅ **User Registration** - Create new user accounts with validation  
✅ **User Login** - Authenticate with credentials  
✅ **User Logout** - Secure session termination  
✅ **Protected Areas** - Dashboard accessible only to authenticated users  
✅ **Password Change** - Users can update their passwords securely  
✅ **User Profile** - View and edit user account information  

### Security Features
- **CSRF Protection** - All forms include `{% csrf_token %}`
- **Brute-Force Protection** - Django-Axes prevents login attacks
- **Secure Password Validation** - Django's built-in password validators
- **SSL/HTTPS Hardening** - Secure cookie flags and HSTS
- **Open Redirect Prevention** - Safe redirect validation using `url_has_allowed_host_and_scheme()`
- **Session Management** - HttpOnly and Secure cookie flags enabled
- **Input Validation** - Custom validators for email uniqueness and name validation
- **XSS Protection** - Enabled via Django's security middleware
- **Clickjacking Protection** - X-Frame-Options set to DENY

---

## Installation

### Prerequisites
- Python 3.9+
- pip (Python package installer)
- Virtual environment (recommended)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd devsec-demo
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (admin account)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Collect static files (optional for development)**
   ```bash
   python manage.py collectstatic --noinput
   ```

---

## Running the Application

### Development Server
```bash
python manage.py runserver
```

Access the application at: `http://localhost:8000`

### Access Points
- **Home/Dashboard**: `http://localhost:8000/` (requires login)
- **Register**: `http://localhost:8000/register/`
- **Login**: `http://localhost:8000/login/`
- **Admin Panel**: `http://localhost:8000/admin/` (requires superuser)

---

## Testing

### Run All Tests
```bash
python manage.py test asher_ndizeye -v 2
```

### Run Specific Test Class
```bash
python manage.py test asher_ndizeye.RegistrationTestCase
python manage.py test asher_ndizeye.LoginTestCase
python manage.py test asher_ndizeye.ProtectedPagesTestCase
```

### Test Coverage
The test suite includes:
- **Registration Tests**: Success and duplicate email validation
- **Login Tests**: Valid credentials, wrong password, open redirect prevention
- **Logout Tests**: Session termination and redirection
- **Protected Access Tests**: Authentication requirement verification
- **Security Tests**: Open redirect prevention, safe redirect handling

---

## Project Structure

```
devsec-demo/
├── asher_ndizeye/                    # Main authentication app
│   ├── migrations/                   # Database migrations
│   ├── templates/asher_ndizeye/      # HTML templates
│   │   ├── base.html                 # Base template with navigation
│   │   ├── register.html             # Registration form
│   │   ├── login.html                # Login form (styled)
│   │   ├── dashboard.html            # Protected dashboard
│   │   ├── profile.html              # User profile page
│   │   └── change_password.html      # Password change form
│   ├── admin.py                      # Django admin configuration
│   ├── apps.py                       # App configuration
│   ├── forms.py                      # Form classes (Registration, Login, Profile)
│   ├── models.py                     # Data models (Profile)
│   ├── tests.py                      # Test suite
│   ├── urls.py                       # URL routing
│   ├── views.py                      # View functions
│   └── __init__.py
├── devsec_demo/                      # Project settings
│   ├── settings.py                   # Django settings
│   ├── urls.py                       # Project URL configuration
│   ├── wsgi.py                       # WSGI application
│   ├── asgi.py                       # ASGI application
│   └── __init__.py
├── manage.py                         # Django management script
├── requirements.txt                  # Python dependencies
├── db.sqlite3                        # SQLite database (development)
├── .env                              # Environment variables (not in repo)
└── README.md                         # This file
```

---

## Authentication Flow

### Registration Flow
```
User → /register/ → RegistrationForm → Profile Created → Redirects to /login/
```

**Required Fields:**
- Username (unique)
- First Name (letters only)
- Last Name (letters only)
- Email (unique)
- Password (must meet Django's password requirements)

**Validation:**
- Email uniqueness check
- Name contains only letters
- Password strength requirements

### Login Flow
```
User → /login/ → LoginForm → Session Created → Redirects to /dashboard/
```

**Features:**
- Brute-force protection (5 attempts, 30-minute lockout)
- Secure redirect validation
- Session management

### Protected Page Flow
```
Unauthenticated User → Protected Page → Redirects to /login/?next=/protected/
Authenticated User → Protected Page → Allowed
```

---

## Security Features

### 1. CSRF Protection
All forms include Django's CSRF token:
```html
<form method="post">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

### 2. Password Security
- **Built-in Validators**: UserAttributeSimilarityValidator, MinimumLengthValidator, CommonPasswordValidator, NumericPasswordValidator
- **Session Preservation**: `update_session_auth_hash()` keeps user logged in after password change

### 3. Authentication Decorators
Protected views use `@login_required`:
```python
@login_required
def dashboard(request):
    return render(request, 'asher_ndizeye/dashboard.html')
```

### 4. Open Redirect Prevention
Validates redirect URLs:
```python
if url_has_allowed_host_and_scheme(
    url=next_url,
    allowed_hosts={request.get_host()},
    require_https=request.is_secure(),
):
    return redirect(next_url)
```

### 5. Brute-Force Protection
Django-Axes middleware blocks after 5 failed login attempts:
```python
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # 30 minutes
```

### 6. Session & Cookie Hardening
```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
```

---

## API Endpoints

### Public Endpoints

| Method | URL | Purpose |
|--------|-----|---------|
| GET/POST | `/register/` | User registration |
| GET/POST | `/login/` | User login |

### Protected Endpoints (Require Authentication)

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/` | Dashboard (home) |
| GET | `/dashboard/` | Dashboard page |
| GET/POST | `/profile/` | User profile |
| GET/POST | `/change-password/` | Change password |
| GET | `/logout/` | Logout |

---

## Admin Interface

Access Django admin at `/admin/` with superuser credentials:

**Available Models:**
- User (Django built-in)
- Profile (Custom user profile)

**Profile Admin Features:**
- List display: User, Created Date
- Search: By username and email

---

## Best Practices Implemented

✅ Follow Django conventions and separation of concerns  
✅ Reuse built-in Django authentication features  
✅ Use secure defaults and avoid insecure shortcuts  
✅ Protect forms with CSRF protection  
✅ Validate user input on form and model boundaries  
✅ Keep URLs, views, templates organized  
✅ Write modular, maintainable code  
✅ Avoid duplicating Django's secure features  
✅ Comprehensive test coverage  
✅ No existing functionality broken  

---

## Environment Variables

Create a `.env` file in the project root (not committed to repo):

```env
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Dependencies

- **Django 6.0.4** - Web framework
- **django-axes** - Brute-force protection
- **python-dotenv** - Environment variable management
- **sqlparse** - SQL parsing
- **asgiref** - ASGI utilities

---

## Testing the Application Manually

### 1. Test Registration
- Navigate to `/register/`
- Enter valid credentials
- Verify success message and redirect to login

### 2. Test Login
- Navigate to `/login/`
- Enter valid credentials
- Verify redirect to dashboard

### 3. Test Protected Areas
- Try accessing `/dashboard/` without login
- Verify redirect to login page

### 4. Test Password Change
- Login, navigate to `/change-password/`
- Enter old and new passwords
- Verify session persistence after change

### 5. Test Logout
- Click logout button
- Verify redirect to login page
- Verify cannot access protected pages

---

## Troubleshooting

### Database Issues
```bash
# Reset database and migrations
python manage.py migrate zero asher_ndizeye
python manage.py migrate

# Or completely reset
rm db.sqlite3
python manage.py migrate
```

### Static Files Not Loading
```bash
python manage.py collectstatic --noinput
```

### Tests Failing
```bash
# Ensure migrations are current
python manage.py migrate

# Run with verbose output
python manage.py test asher_ndizeye -v 2
```

---

## Contributing

This is a learning project. For improvements or bug fixes:
1. Create a new branch from `assignment/uas-auth-service`
2. Make changes
3. Run tests
4. Submit pull request

---

## License

This project is part of a Django security training course.
