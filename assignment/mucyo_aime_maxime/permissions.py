"""
Authorization and permission decorators for role-based access control.

This module provides decorators for enforcing role-based authorization
in the UAS application. Three distinct roles are supported:
- Anonymous users (no authentication required)
- Authenticated users (logged in)
- Staff/privileged users (group membership)

Also includes object-level access control for preventing IDOR vulnerabilities.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User


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


def user_owns_object(view_func):
    """
    Object-level access control decorator to prevent IDOR vulnerabilities.
    
    Ensures that a user can only access/modify objects that belong to them.
    The view must accept a 'user_id' parameter and the current user must 
    either be the owner of that user ID or a superuser.
    
    This decorator checks that:
    - The user is authenticated
    - The requested user_id exists
    - The requesting user owns the object (is the same user) or is a superuser
    
    Unauthorized access returns a 403 Forbidden response.
    """
    @wraps(view_func)
    def wrapper(request, user_id=None, *args, **kwargs):
        # Ensure the user is authenticated
        if not request.user.is_authenticated:
            messages.warning(request, 'You must log in to access this page.')
            return redirect('mucyo_aime_maxime:login')
        
        # If user_id is provided, check ownership
        if user_id is not None:
            # Verify the requested user exists
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return redirect('mucyo_aime_maxime:profile')
            
            # Check if current user is the owner or a superuser (IDOR prevention)
            if request.user.id != user_id and not request.user.is_superuser:
                messages.error(request, 'You do not have permission to access this resource.')
                return HttpResponseForbidden('Access Denied: You cannot access other users\' data.')
        
        return view_func(request, user_id=user_id, *args, **kwargs)
    return wrapper
