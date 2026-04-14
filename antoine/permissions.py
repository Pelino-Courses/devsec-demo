"""
Permission decorators and utilities for role-based access control.
These decorators provide easy-to-read permission checks for views.
"""
from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def get_user_role(user):
    """
    Determine the role of a user based on group membership.
    
    Returns: 'admin', 'instructor', 'student', or 'anonymous'
    """
    if not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser or user.groups.filter(name='Admin').exists():
        return 'admin'
    if user.groups.filter(name='Instructor').exists():
        return 'instructor'
    if user.groups.filter(name='Student').exists():
        return 'student'
    # Default to student if authenticated but not in any group
    return 'student'


def has_permission(user, perm_codename):
    """
    Check if user has a specific permission.
    
    Args:
        user: Django User instance
        perm_codename: Permission codename (e.g., 'view_all_users_profile')
    
    Returns: Boolean
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_perm(f'antoine.{perm_codename}')


def is_admin(user):
    """Check if user is an admin (superuser or Admin group)"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Admin').exists())


def is_instructor(user):
    """Check if user is an instructor or admin"""
    return user.is_authenticated and (is_admin(user) or user.groups.filter(name='Instructor').exists())


def is_authenticated(user):
    """Check if user is authenticated"""
    return user.is_authenticated


# Decorator: Require admin role
def admin_required(view_func):
    """Decorator to require admin role. Redirects to login if not authorized."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('antoine:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# Decorator: Require instructor or admin role
def instructor_required(view_func):
    """Decorator to require instructor or admin role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_instructor(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('antoine:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# Decorator: Require specific permission
def permission_required(perm_codename):
    """Decorator to require a specific permission."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, perm_codename):
                messages.error(request, 'You do not have permission to perform this action.')
                return redirect('antoine:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Decorator: Allow anonymous, but provide role info
def optional_login(view_func):
    """Decorator that allows both authenticated and unauthenticated users."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Attach role info to request for use in view
        request.user_role = get_user_role(request.user)
        return view_func(request, *args, **kwargs)
    return wrapper
