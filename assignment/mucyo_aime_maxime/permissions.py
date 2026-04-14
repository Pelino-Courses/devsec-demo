"""
Authorization and permission decorators for role-based access control.

This module provides decorators for enforcing role-based authorization
in the UAS application. Three distinct roles are supported:
- Anonymous users (no authentication required)
- Authenticated users (logged in)
- Staff/privileged users (group membership)
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def user_is_authenticated(view_func):
    """
    Decorator to restrict access to authenticated users only.
    
    Anonymous users are redirected to login page with a message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'You must log in to access this page.')
            return redirect('mucyo_aime_maxime:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def user_is_staff(view_func):
    """
    Decorator to restrict access to staff members only.
    
    Requirements:
    - User must be authenticated
    - User must be in 'Staff' group OR be a superuser
    
    Unauthorized users receive a 403 response.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'You must log in to access this page.')
            return redirect('mucyo_aime_maxime:login')
        
        # Check if user is staff or in Staff group
        is_staff = request.user.is_staff or request.user.is_superuser
        is_in_staff_group = request.user.groups.filter(name='Staff').exists()
        
        if not (is_staff or is_in_staff_group):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('mucyo_aime_maxime:profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def user_is_instructor(view_func):
    """
    Decorator to restrict access to instructors only.
    
    Requirements:
    - User must be authenticated
    - User must be in 'Instructor' group OR be a superuser
    
    Unauthorized users receive a 403 response.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'You must log in to access this page.')
            return redirect('mucyo_aime_maxime:login')
        
        # Check if user is instructor or superuser
        is_instructor = request.user.groups.filter(name='Instructor').exists()
        is_superuser = request.user.is_superuser
        
        if not (is_instructor or is_superuser):
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('mucyo_aime_maxime:profile')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def check_user_role(user):
    """
    Utility function to determine the user's role.
    
    Returns one of: 'anonymous', 'user', 'staff', 'instructor', 'admin'
    """
    if not user.is_authenticated:
        return 'anonymous'
    
    if user.is_superuser:
        return 'admin'
    
    if user.groups.filter(name='Instructor').exists():
        return 'instructor'
    
    if user.groups.filter(name='Staff').exists() or user.is_staff:
        return 'staff'
    
    return 'user'
