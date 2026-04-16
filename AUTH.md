# Authorization Strategy

## Overview

This document describes the role-based access control (RBAC) system implemented for the User Authentication Service (UAS).

## Authorization Model

### Roles

The system defines four user roles:

| Role | Description | Access Level |
|------|------------|-------------|
| `user` | Standard User | Basic |
| `instructor` | Instructor | Privileged |
| `staff` | Staff Member | Privileged |
| `admin` | Administrator | Full |

### Access Matrix

| Action | Anonymous | User | Instructor/Staff | Admin |
|--------|----------|------|---------------|------|
| View Login Page | ✓ | - | - | - |
| View Register Page | ✓ | - | - | - |
| View Own Profile | - | ✓ | ✓ | ✓ |
| Edit Own Profile | - | ✓ | ✓ | ✓ |
| Change Password | - | ✓ | ✓ | ✓ |
| Admin Dashboard | - | ✗ | ✓ | ✓ |
| View All Profiles | - | ✗ | ✓ | ✓ |
| User Management | - | ✗ | ✗ | ✓ |
| Change User Roles | - | ✗ | ✗ | ✓ |

## Implementation Details

### Custom Permissions

The system uses Django's native groups and permissions:

- **Privileged Group**: Contains `view_privileged`, `manage_users`, and `view_all_profiles` permissions
- **Standard Group**: Contains `view_privileged` permission

### Decorators

- `@login_required`: Requires authentication
- `@privileged_required`: Requiresprivileged role (instructor, staff, admin)
- `@admin_required`: Requires admin role
- `@role_required(allowed_roles)`: Requires specific role(s)

### URL Access Control

All privileged endpoints require authentication and appropriate role permissions.

### Template Context

The `role_context` processor adds role information to all templates:

- `user_role`: Current user's role
- `is_privileged`: Boolean indicating privileged status
- `is_admin`: Boolean indicating admin status

## Tradeoffs and Design Decisions

### Why Django Groups and Permissions?

1. **Native Solution**: Uses Django's built-in authorization system, reducing maintenance overhead
2. **Audit Trail**: Permissions can be tracked and managed through admin interface
3. **Scalability**: Easy to add new roles and permissions

### Why Not Ad Hoc Role Checks?

1. **Maintainability**: Ad hoc checks scatter authorization logic
2. **Testability**: Decorators are easier to test than inline checks
3. **Consistency**: Centralized access control logic

### Security Considerations

- **Separation of Concerns**: Authentication (who) is separate from authorization (what they can do)
- **Least Privilege**: Users only get the minimum permissions needed
- **Defense in Depth**: Multiple layers of access control (URL, view, template)
- **Safe Defaults**: Deny all access by default

### Limitations

- Role changes require profile save (automatic via Profile.save())
- Staff flag is automatically set for admin users
- Cannot downgrade your own admin role through the UI

## Testing

Run tests with:

```bash
python manage.py test justin.tests.RoleBasedAccessControlTest
```

Tests cover:
- Anonymous access to public pages
- Standard user access to privileged pages (denied)
- Privileged user access to admin pages (partial)
- Admin user access to all pages
- 403 error handling