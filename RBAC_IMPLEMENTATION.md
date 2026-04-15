# RBAC Implementation - Commit Summary

## Branch: `assignment/role-based-access-control`

### Overview

This commit implements **Role-Based Access Control (RBAC)** for the User Authentication Service (UAS), enabling fine-grained authorization based on user roles. The implementation uses Django's built-in Groups and Permissions system to define and enforce distinct access expectations for anonymous users, authenticated students, instructors, staff, and system administrators.

### Key Features Implemented

#### 1. Authorization Framework (`aline/decorators.py`)
- **Helper Functions**:
  - `get_user_role()` - Determine user's primary role
  - `is_admin()`, `is_staff_or_admin()`, `is_instructor_or_above()` - Permission checks
  
- **Decorators**:
  - `@admin_required` - Restrict to admin users
  - `@staff_required` - Restrict to staff/admin
  - `@instructor_required` - Restrict to instructor/staff/admin
  - `@student_required` - Require authentication
  
- **Mixin**:
  - `RoleRequiredMixin` - For class-based views with role checking

#### 2. Role Initialization (`aline/management/commands/setup_roles.py`)
- Creates four Django Groups: Student, Instructor, Staff, Admin
- Assigns appropriate permissions to each role
- Provides clear output showing role and permission setup
- Run via: `python manage.py setup_roles`

#### 3. Enhanced Views (`aline/views.py`)
- **Updated existing views** with role information in context:
  - `HomeView` - Shows role-aware content
  - `DashboardView` - Includes role information
  
- **New admin/staff views**:
  - `AdminDashboardView` - Admin-only dashboard with system statistics
  - `UserManagementView` - Staff-only user list with pagination
  - `UserDetailView` - Staff-only user detail and role assignment
  - `StudentListView` - Instructor-accessible student list

#### 4. URL Routing (`aline/urls.py`)
- Added protected routes with role-based access:
  - `/admin/dashboard/` - Admin dashboard (admin-only)
  - `/admin/users/` - User management list (staff-only)
  - `/admin/users/<id>/` - User detail and role assignment (staff-only)
  - `/instructor/students/` - Student list (instructor-only)

#### 5. Enhanced Admin Interface (`aline/admin.py`)
- Improved `UserProfileAdmin` with:
  - Group/role display in user list
  - Group filtering
  - Better search functionality
  
- Registered `GroupAdmin` to show:
  - Member count per group
  - Permission count per group
  - Better group management

#### 6. Admin Templates
- **`aline/templates/aline/admin/admin_dashboard.html`**:
  - System statistics (users, profiles, roles)
  - Role distribution overview
  - Recent users list
  - Management tools dashboard
  
- **`aline/templates/aline/admin/user_management.html`**:
  - Paginated user list
  - Role display for each user
  - Access to user detail views
  - Statistics cards
  
- **`aline/templates/aline/admin/user_detail.html`**:
  - User information display
  - Current role assignment
  - Role assignment form
  - Role descriptions and documentation

#### 7. Instructor Templates
- **`aline/templates/aline/instructor/student_list.html`**:
  - Paginated student list
  - Student ID, email, name display
  - Access control information
  - Instructor-specific messaging

#### 8. Comprehensive Tests (`aline/tests_rbac.py`)
- **Role Detection Tests**:
  - `RoleBasedAccessControlTestCase` - Tests for role detection and permission functions
  - Covers: anonymous, student, instructor, staff, admin users
  
- **Access Control Tests**:
  - `AdminViewAccessControlTestCase` - Tests admin dashboard access
  - `StaffViewAccessControlTestCase` - Tests staff functions access
  - `InstructorViewAccessControlTestCase` - Tests instructor functions access
  
- **Security Tests**:
  - `UnauthorizedAccessAttemptTestCase` - Ensures 403 responses for unauthorized access
  - `RoleBasedViewContextTestCase` - Verifies role info in templates

#### 9. Documentation (`docs/RBAC.md`)
- Overview of RBAC system
- Complete role hierarchy explanation
- Implementation details
- Access control rules and route mappings
- Security considerations
- Testing procedures
- Role assignment instructions
- Common usage patterns
- Troubleshooting guide

### Security Features

1. **Principle of Least Privilege**: Each role gets only necessary permissions
2. **Server-Side Enforcement**: All authorization checks server-side (not client-side)
3. **Decorator-Based Protection**: Views automatically protected via decorators
4. **Safe Error Handling**: HTTP 403 for unauthorized access, HTTP 302 redirect for unauthenticated
5. **No IDOR Risk**: Users cannot access resources their role doesn't permit
6. **Privilege Escalation Prevention**: Permissions validated for all operations

### Usage

#### Initialize Roles
```bash
python manage.py setup_roles
```

#### Assign Roles to Users
1. Via Django admin (`/admin/`)
2. Via staff interface (`/admin/users/<id>/`)
3. Programmatically in code

#### Check Permissions in Code
```python
from aline.decorators import is_admin, is_staff_or_admin

if is_admin(request.user):
    # Admin-only logic
    pass
```

#### Protect Views
```python
from aline.decorators import admin_required

@admin_required
def admin_view(request):
    # Only admins can access
    pass
```

#### Hide UI Elements
```html
{% if is_admin %}
  <!-- Show admin-only content -->
{% endif %}
```

### Testing

Run RBAC tests:
```bash
# All RBAC tests
python manage.py test aline.tests_rbac

# Specific test class
python manage.py test aline.tests_rbac.AdminViewAccessControlTestCase

# Verbose output
python manage.py test aline.tests_rbac -v 2
```

Test coverage includes:
- ✅ Role detection for all user types
- ✅ Permission validation functions
- ✅ View access control enforcement
- ✅ Unauthorized access handling (403, 302)
- ✅ Template context role information

### Files Changed

- **Created**:
  - `aline/decorators.py` - RBAC decorators and helpers
  - `aline/management/commands/setup_roles.py` - Role initialization
  - `aline/tests_rbac.py` - Comprehensive RBAC tests
  - `aline/templates/aline/admin/admin_dashboard.html`
  - `aline/templates/aline/admin/user_management.html`
  - `aline/templates/aline/admin/user_detail.html`
  - `aline/templates/aline/instructor/student_list.html`
  - `docs/RBAC.md` - Complete RBAC documentation

- **Modified**:
  - `aline/views.py` - Added role checking, new protected views
  - `aline/urls.py` - Added protected route patterns
  - `aline/admin.py` - Enhanced with role information display

### Backward Compatibility

- ✅ Existing authentication system unchanged
- ✅ All existing tests continue to pass
- ✅ No breaking changes to current routes
- ✅ Users without assigned roles default to 'student' status
- ✅ Anonymous users still access public pages

### Authorization Strategy & Tradeoffs

#### Strategy: Django Native Groups & Permissions
- **Pros**:
  - Built-in Django support - well-tested and documented
  - Flexible permission model
  - Easy UI integration (Django admin)
  - Scalable to fine-grained permissions
  
- **Cons**:
  - Slightly more database queries
  - Role hierarchy not built-in (implemented manually)
  
- **The Tradeoff**: Used Django Groups (coarser-grained, simpler) rather than object-level permissions (finer-grained, more complex) for this initial implementation to balance security with maintainability.

### Testing Verification

All tests pass:
```
✅ RoleBasedAccessControlTestCase (8 tests)
✅ AdminViewAccessControlTestCase (4 tests)
✅ StaffViewAccessControlTestCase (3 tests)
✅ InstructorViewAccessControlTestCase (3 tests)
✅ UnauthorizedAccessAttemptTestCase (2 tests)
✅ RoleBasedViewContextTestCase (1 test)

Total: 21 tests covering all RBAC scenarios
```

### Commits in This PR

1. `feat: Add RBAC decorators and helper functions`
   - Implements authorization framework
   - Provides decorators for view protection

2. `feat: Add role initialization management command`
   - Creates Django groups and assigns permissions
   - Provides setup/configuration automation

3. `feat: Add protected admin and instructor views`
   - Implements role-based view protection
   - Adds user management and student list views

4. `feat: Add admin and instructor templates`
   - Creates UI for admin dashboard
   - Includes user management interface
   - Adds instructor student view

5. `test: Add comprehensive RBAC access control tests`
   - Tests all role detection scenarios
   - Tests view access control enforcement
   - Tests unauthorized access handling

6. `docs: Add RBAC implementation documentation`
   - Complete system documentation
   - Role hierarchy explanation
   - Usage patterns and examples
   - Security considerations

### Conclusion

This RBAC implementation provides a solid foundation for authorization in the UAS. It follows Django best practices, uses well-established patterns, and is thoroughly tested. The system is:

- **Secure**: Enforces least privilege and prevents privilege escalation
- **Maintainable**: Clear code structure, well-documented
- **Extensible**: Easy to add more sophisticated permissions later
- **User-Friendly**: Web UI for role management
- **Well-Tested**: Comprehensive test coverage

The implementation successfully addresses the learning objectives:
- ✅ Design and enforce authorization rules in Django
- ✅ Separate concerns: authentication vs authorization  
- ✅ Implement role-aware behavior throughout application
- ✅ Use Django-native groups and permissions
- ✅ Comprehensive testing of access control paths
- ✅ Existing behavior preserved
