# Role-Based Access Control (RBAC) Implementation

## Overview

This document describes the Role-Based Access Control (RBAC) system implemented for the User Authentication Service (UAS) application. The RBAC system enforces authorization rules based on user roles, ensuring that only authorized users can access sensitive operations.

## Authorization Model

The system implements a **four-tier role hierarchy** using Django's built-in Groups and Permissions model:

### Role Hierarchy

```
Anonymous (Not Authenticated)
  ├── Can: View home page, register, login
  └── Cannot: Access protected pages, manage users

Student (Authenticated, Basic User)
  ├── Can: View own profile, change own password, access dashboard
  ├── Cannot: Access admin/staff functions
  └── Permissions: Limited to own data

Instructor (Teaching Role)
  ├── Can: View all student profiles, access instructor dashboard
  ├── Can: View student list with detailed information
  └── Cannot: Modify student data or system settings

Staff (Administrative Role)
  ├── Can: Do everything Instructor can do
  ├── Can: Manage user accounts, assign roles/permissions
  ├── Can: View detailed system information
  └── Cannot: Access full admin backend (Django admin)

Admin (Full System Control)
  ├── Can: Do everything Staff can do
  ├── Can: Access Django admin interface
  ├── Can: Modify system settings and configurations
  └── Permissions: Unrestricted access (is_superuser=True)
```

## Implementation Details

### Key Components

1. **Decorators** (`decorators.py`):
   - `@admin_required` - Restrict access to admin users only
   - `@staff_required` - Restrict access to staff and admin
   - `@instructor_required` - Restrict access to instructors and above
   - `@student_required` - Require authentication
   - `RoleRequiredMixin` - For class-based views

2. **Helper Functions** (`decorators.py`):
   - `get_user_role()` - Determine user's primary role
   - `is_admin()` - Check if user is admin
   - `is_staff_or_admin()` - Check if user is staff or admin
   - `is_instructor_or_above()` - Check if user is instructor or higher

3. **Management Command** (`management/commands/setup_roles.py`):
   - Initializes Django Groups
   - Creates roles and assigns permissions
   - Run: `python manage.py setup_roles`

4. **Views** (`views.py`):
   - Protected views with role-based access decorators
   - Role information added to template context
   - Safe error handling for unauthorized access

### Database Model

#### Groups (Django Built-in)

```python
Group
├── Student
├── Instructor
├── Staff
└── Admin
```

### URL Routes with RBAC

| Route | Method | Required Role | Description |
|-------|--------|---------------|-------------|
| `/` | GET | Anyone | Public home page |
| `/register/` | GET, POST | Anonymous | User registration |
| `/login/` | GET, POST | Anonymous | User login |
| `/logout/` | GET | Authenticated | User logout |
| `/dashboard/` | GET | Authenticated | Personal dashboard |
| `/profile/` | GET, POST | Authenticated | User profile |
| `/change-password/` | GET, POST | Authenticated | Change password |
| `/management/dashboard/` | GET | Admin | Admin statistics |
| `/management/users/` | GET | Staff+ | User management list |
| `/management/users/<id>/` | GET, POST | Staff+ | User detail & role assignment |
| `/management/students/` | GET | Instructor+ | Student list |

## Access Control Enforcement

### View-Level Protection

#### Example: Admin-Only View

```python
from aline.decorators import admin_required

@admin_required
def sensitive_admin_view(request):
    # Only admins can access this
    return render(request, 'admin/dashboard.html')
```

#### Example: Role-Required Mixin

```python
from aline.decorators import RoleRequiredMixin

class StaffOnlyView(RoleRequiredMixin, TemplateView):
    role_required = 'staff'
    template_name = 'admin/management.html'
```

### Template-Level Protection

```html
<!-- Show admin-only content -->
{% if is_admin %}
  <a href="{% url 'aline:admin_dashboard' %}">Admin Dashboard</a>
{% endif %}

<!-- Show instructor-or-above content -->
{% if is_instructor %}
  <a href="{% url 'aline:student_list' %}">View Students</a>
{% endif %}
```

## Security Considerations

### Least Privilege Principle

- Each role is granted **only the minimum permissions** necessary for its function
- Students cannot see admin features in templates
- Protected views check permissions server-side (not trusting client-side logic)

### Prevention of Unauthorized Access

1. **View-Level Checks**: Every protected view validates user permissions
2. **Template-Level Filters**: UI elements hidden from unauthorized users
3. **Safe Error Handling**: Returns HTTP 403 (Forbidden) for unauthorized access
4. **No IDOR Risk**: Users can only access resources their role permits

### Attack Prevention

#### Privilege Escalation Prevention

```python
# Views check actual user role, not request parameters
@staff_required
def manage_users(request):
    # Attacker cannot bypass by modifying URL or POST data
    # The decorator validates permission before view executes
```

#### Broken Access Control Prevention

```python
# All protected routes enforced with decorators
# No bypassing through URL manipulation
@staff_required
def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    # Cannot access if not staff, regardless of user_id
```

## Testing

### Test Coverage

The RBAC system includes comprehensive tests in `tests_rbac.py`:

- ✅ Role detection for all user types
- ✅ Permission check functions
- ✅ Admin-only view access control
- ✅ Staff-only view access control
- ✅ Instructor view access control
- ✅ Unauthorized access handling
- ✅ Context variable inclusion

### Running Tests

```bash
# Run all RBAC tests
python manage.py test aline.tests_rbac

# Run specific test class
python manage.py test aline.tests_rbac.AdminViewAccessControlTestCase

# Run with verbose output
python manage.py test aline.tests_rbac -v 2
```

## Role Assignment

### Assigning Roles to Users

#### Via Django Admin

1. Navigate to `/admin/` (requires superuser)
2. Select "Groups"
3. Click on a role (Student, Instructor, Staff, Admin)
4. Add users to the group

#### Via User Detail View

1. Staff/Admin navigate to `/management/users/`
2. Click "Manage" on a user
3. Select roles via checkboxes
4. Click "Save Changes"

#### Via Management Command

```python
from django.contrib.auth.models import User, Group

user = User.objects.get(username='john')
student_group = Group.objects.get(name='Student')
user.groups.add(student_group)
```

## Common Patterns

### Checking Permissions in Views

```python
from aline.decorators import is_admin, is_staff_or_admin

def my_view(request):
    if is_admin(request.user):
        # Admin-specific logic
        pass
    elif is_staff_or_admin(request.user):
        # Staff-specific logic
        pass
    else:
        # Regular user logic
        pass
```

### Conditional Template Display

```html
{% load user_tags %}

<!-- Show different content based on role -->
{% if user.is_authenticated %}
  <h1>Welcome, {{ user.username }}!</h1>
  
  {% if is_admin %}
    <p>You have admin access</p>
  {% elif is_staff %}
    <p>You have staff access</p>
  {% elif is_instructor %}
    <p>You have instructor access</p>
  {% else %}
    <p>You are a student</p>
  {% endif %}
{% else %}
  <p>Please log in</p>
{% endif %}
```

## Troubleshooting

### User Cannot Access Protected View

1. **Check group membership**: 
   - Go to Django admin `/admin/`
   - Check user's groups in their profile

2. **Verify permissions**:
   - Run `python manage.py setup_roles` to ensure groups exist
   - Check that groups have required permissions

3. **Clear cache/sessions**:
   - User may need to log out and log back in
   - Clear browser cookies/cache

### Role Not Appearing in Context

- Ensure user is assigned to a group
- Verify group name exactly matches (case-sensitive)
- Check that view uses role-aware context

## Future Enhancements

1. **Fine-Grained Permissions**: Implement object-level permissions
2. **Permission Management UI**: Allow admins to modify permissions via web interface
3. **Audit Logging**: Track who accessed what and when
4. **Time-Based Access**: Implement temporary role elevation for specific tasks
5. **Permission Inheritance**: Automatic permission cascading based on role hierarchy

## Conclusion

The RBAC system provides a secure, maintainable authorization model for the UAS application. By using Django's built-in Groups and Permissions, it ensures:

- Clear role definitions
- Easy permission management
- Secure access control enforcement
- Comprehensive testing and audit trails
- Easy to understand and modify

This foundation can be extended with more sophisticated permission models as the application grows.
