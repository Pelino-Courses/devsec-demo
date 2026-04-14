# Student Portal - Production-Ready Authentication System

## 🚀 Quick Start

### 1. Setup Database & Sample Data

```bash
# Apply migrations
python manage.py migrate

# Create 4 sample students (default password: user@123)
python manage.py create_sample_students
```

### 2. Run Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000

### 3. Login with Demo Accounts

**Test Credentials:**

- **Username**: student1 | **Password**: user@123
- **Username**: student2 | **Password**: user@123
- **Username**: student3 | **Password**: user@123
- **Username**: student4 | **Password**: user@123

---

## 📚 Documentation

For comprehensive documentation, see [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)

**Key Sections:**

- Architecture & Design
- Security Implementation
- API Endpoints
- Testing Guide
- Troubleshooting

---

## ✨ Features

✅ **User Registration** - Email & student ID validation  
✅ **Secure Login** - Username or email support  
✅ **Protected Dashboard** - Authenticated-only access  
✅ **Profile Management** - View and update student info  
✅ **Password Change** - Current password verification  
✅ **CSRF Protection** - On all POST forms  
✅ **Password Hashing** - PBKDF2 with Django auth  
✅ **Access Control** - @login_required decorators

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test aline_uwamahoro.tests

# Run with coverage
coverage run --source='aline_uwamahoro' manage.py test
coverage report
```

**Test Coverage:** 24+ test cases covering:

- Registration flow
- Login/logout
- Access control
- Password change
- Profile management

---

## 🛠️ Admin Interface

Access Django admin at: http://localhost:8000/admin/

**Default Credentials:** Create a superuser:

```bash
python manage.py createsuperuser
```

---

## 📁 Key Files

| File                         | Purpose                             |
| ---------------------------- | ----------------------------------- |
| `aline_uwamahoro/models.py`  | UserProfile model                   |
| `aline_uwamahoro/forms.py`   | Registration, login, password forms |
| `aline_uwamahoro/views.py`   | View logic (auth flow)              |
| `aline_uwamahoro/urls.py`    | URL routing                         |
| `aline_uwamahoro/templates/` | HTML templates                      |
| `docs/AUTHENTICATION.md`     | Full documentation                  |

---

## 🔐 Security Highlights

- **Password Hashing**: PBKDF2 with 260K iterations
- **CSRF Protection**: Enabled on all forms
- **Input Validation**: Server-side form validation
- **SQL Injection**: Prevented by Django ORM
- **XSS Prevention**: Template auto-escaping
- **Session Security**: Secure cookie configuration
- **Generic Errors**: Prevents username enumeration

---

## 📋 URL Routes

| Route               | Purpose                     |
| ------------------- | --------------------------- |
| `/`                 | Home page                   |
| `/register/`        | Registration form           |
| `/login/`           | Login form                  |
| `/logout/`          | Logout                      |
| `/dashboard/`       | User dashboard (protected)  |
| `/profile/`         | Profile page (protected)    |
| `/change-password/` | Password change (protected) |
| `/admin/`           | Django admin                |

---

## 🐛 Troubleshooting

**"Table does not exist"**

```bash
python manage.py migrate
```

**"Module not found"**

```bash
pip install -r requirements.txt
```

**"Login fails"**

```bash
# In Django shell
python manage.py shell
from django.contrib.auth.models import User
user = User.objects.get(username='student1')
user.set_password('user@123')
user.save()
```

---

## 📖 Learn More

- [Full Documentation](docs/AUTHENTICATION.md)
- [Django Security Docs](https://docs.djangoproject.com/en/6.0/topics/security/)
- [Django Auth System](https://docs.djangoproject.com/en/6.0/topics/auth/)

---

## ✅ Checklist

- [x] User registration with validation
- [x] Login/logout functionality
- [x] Password change with verification
- [x] Profile management
- [x] CSRF protection
- [x] Access control
- [x] Password hashing
- [x] Sample data (4 students)
- [x] Comprehensive tests (24+)
- [x] Documentation
- [x] admin.py configuration
- [x] Template inheritance
- [x] Responsive UI (Bootstrap 5)

---

**Status**: ✅ Production-Ready  
**Version**: 1.0  
**Django**: 6.0.4  
**Python**: 3.8+
