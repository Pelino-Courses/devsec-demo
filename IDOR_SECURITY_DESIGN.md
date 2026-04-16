# IDOR Prevention: Design Notes and Security Decisions

## Overview

This pull request implements **Insecure Direct Object Reference (IDOR)** prevention in user profile and account management views. IDOR vulnerabilities occur when an application uses user-supplied input to perform direct database lookups without verifying that the user is authorized to access that specific resource.

## IDOR Vulnerability Analysis

### Attack Scenario
Before this fix, a malicious user could:
1. Predict or guess other users' profile URLs (e.g., `/users/2/profile/`)
2. Modify their own user ID in account URLs to access other users' data
3. Change email addresses or other profile information for users they don't own

### Root Cause
The previous implementation lacked **object-level access control**, which defines:
- **Authentication**: Is the user logged in? ✓ (was checked)
- **Authorization**: Can this logged-in user access THIS resource? ✗ (was missing)

## Implementation: Object-Level Access Control

### 1. **view_user_profile(request, user_id)** - NEW VIEW

**IDOR Protection:**
```python
if request.user != target_user and not request.user.has_perm("uwamahoro_joseline.can_view_all_profiles"):
    raise PermissionDenied("You do not have permission to view this profile.")
```

**Access Rules:**
- ✓ Users can view their OWN profile
- ✓ Instructors with `can_view_all_profiles` permission can view ANY profile
- ✗ Regular students cannot view other students' profiles
- ✗ Unauthenticated users get redirected to login

**Safe Design Decisions:**
- Uses explicit comparison (`request.user != target_user`)
- Raises `PermissionDenied` (403) instead of hiding the user exists
- Does not leak user existence information unnecessarily
- Uses Django's built-in permission system

---

### 2. **edit_user_account(request, user_id)** - NEW VIEW

**IDOR Protection:**
```python
if request.user != target_user:
    raise PermissionDenied("You do not have permission to edit this account.")
```

**Access Rules:**
- ✓ Users can ONLY edit their OWN account
- ✗ Instructors CANNOT bypass this (stricter than profile viewing)
- ✗ All other users are denied

**Safe Design Decisions:**
- Uses strict ownership check (no permission bypass for instructors)
- Prevents privilege escalation attacks
- Returns 404 for non-existent users to avoid information leakage
- Validates email before creating duplicate entries

---

### 3. **promote_user_view(request, user_id)** - ENHANCED

**Additional IDOR Protection:**
```python
# Prevent self-promotion/demotion
if request.user == target_user:
    messages.error(request, "You cannot modify your own role.")
    return redirect("uwamahoro_joseline:instructor_panel")
```

**Access Rules:**
- ✓ Instructors with `can_manage_users` permission can promote/demote students
- ✗ Instructors CANNOT modify their own roles (prevents privilege escalation)
- ✗ Students cannot access this view at all
- ✗ Explicit error message guides users away from tampering

**Safe Design Decisions:**
- Permission check comes FIRST (fail-fast principle)
- Self-modification prevented even with valid permissions
- Informative messages without security leakage
- POST-only (GET attempts are ignored)

---

## URL Routes Added

```python
path("users/<int:user_id>/profile/", views.view_user_profile, name="view_user_profile"),
path("users/<int:user_id>/account/", views.edit_user_account, name="edit_user_account"),
```

Both routes are `@login_required` - authentication is the first check before object-level authorization.

## Test Coverage

### Valid Access Cases
✓ User views their own profile  
✓ User edits their own account  
✓ Instructor views any profile (with permission)  
✓ Instructor promotes/demotes other users  

### Forbidden Access Cases
✗ Student views another student's profile → 403 Forbidden  
✗ Student edits another student's account → 403 Forbidden  
✗ Student promotes another student → 403 Forbidden  
✗ Instructor edits another instructor's account → 403 Forbidden  
✗ Instructor promotes/demotes themselves → Error message + 302 Redirect  

### Authentication Cases
- Unauthenticated users → 302 Redirect to login
- Non-existent users → 404 Not Found

## Django Security Best Practices Applied

| Practice | Implementation |
|----------|-----------------|
| **@login_required** | Protects all new views |
| **@instructor_required** | Custom decorator for role-based access |
| **get_object_or_404()** | Returns 404, prevents user enumeration |
| **PermissionDenied exception** | Raises HTTP 403, proper HTTP semantics |
| **has_perm()** | Django's built-in permission system |
| **Explicit checks** | No implicit assumptions based on login state |
| **CSRF protection** | {% csrf_token %} in forms, POST-only actions |

## Testing Strategy

**Unit Tests:**
- Test each access control rule independently
- Test permission combinations
- Test edge cases (self-modification, non-existent users)

**Integration Tests:**
- Verify `@login_required` decorator works
- Verify `@instructor_required` decorator works
- Verify permission checks with real Group/Permission objects

**Manual Testing:**
- Test from different user roles
- Test URL manipulation attempts
- Verify error messages don't leak information

## Security Impact

**Vulnerabilities Fixed:**
- ✓ IDOR: Users cannot access other users' profiles by URL manipulation
- ✓ IDOR: Users cannot edit other users' accounts
- ✓ Privilege Escalation: Instructors cannot self-modify roles
- ✓ Information Disclosure: Limited error messages prevent user enumeration

**Risk Mitigation:**
- Existing functionality remains unchanged for authorized users
- All access decisions are explicit and auditable
- Principle of least privilege enforced throughout

## Files Modified

1. `uwamahoro_joseline/views.py`
   - Added `view_user_profile()`
   - Added `edit_user_account()`
   - Enhanced `promote_user_view()` with self-modification prevention

2. `uwamahoro_joseline/urls.py`
   - Added two new URL patterns for the new views

3. `uwamahoro_joseline/tests.py`
   - Added 21 new test cases in `IDORProtectionViewUserProfileTests`
   - Added 7 new test cases in `IDORProtectionEditUserAccountTests`
   - Added 4 new test cases in `IDORProtectionPromoteUserTests`

4. `uwamahoro_joseline/templates/uwamahoro_joseline/edit_account.html`
   - New template for the account editing interface

## Backward Compatibility

✓ All existing views and routes remain unchanged  
✓ Existing tests continue to pass  
✓ No database migrations required  
✓ No changes to public API contracts  

## How This Addresses the Learning Objective

Students working through this assignment will learn:

1. **IDOR as a critical vulnerability**: Understanding that login ≠ authorization
2. **Object-level access control**: Implementing per-resource permission checks
3. **Django security patterns**: Using decorators, has_perm(), PermissionDenied
4. **Secure API design**: Using explicit checks instead of implicit assumptions
5. **Testing security controls**: Writing tests for both allowed and forbidden access

---

**Author's Note:** This implementation was created to demonstrate proper IDOR prevention techniques. All code was written to be clear and auditable, with security comments explaining the rationale for each access control decision.
