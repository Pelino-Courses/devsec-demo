"""
Role-based access control decorators and utilities for the aline app.

This module provides decorators and helper functions to enforce authorization
rules in views, ensuring that only users with appropriate roles/permissions
can access sensitive operations.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages


def get_user_role(user):
    """
    Determine the primary role of a user based on group membership.
    
    Returns:
        str: One of 'admin', 'staff', 'instructor', 'student', or 'anonymous'
    """
    if not user.is_authenticated:
        return 'anonymous'
    
    if user.is_superuser or user.is_staff:
        return 'admin'
    
    # Check group membership
    groups = user.groups.values_list('name', flat=True)
    
    if 'Admin' in groups:
        return 'admin'
    elif 'Staff' in groups:
        return 'staff'
    elif 'Instructor' in groups:
        return 'instructor'
    elif 'Student' in groups:
        return 'student'
    else:
        # User is authenticated but not assigned a group
        return 'student'


def is_admin(user):
    """Check if user is an admin."""
    return user.is_superuser or user.is_staff or user.groups.filter(name='Admin').exists()


def is_staff_or_admin(user):
    """Check if user is staff or admin."""
    return is_admin(user) or user.groups.filter(name='Staff').exists()


def is_instructor_or_above(user):
    """Check if user is instructor, staff, or admin."""
    return is_staff_or_admin(user) or user.groups.filter(name='Instructor').exists()


def admin_required(view_func):
    """
    Decorator to restrict view access to admin users only.
    
    Usage:
        @admin_required
        def my_admin_view(request):
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access Denied')
        return view_func(request, *args, **kwargs)
    
    return login_required(wrapped_view)


def staff_required(view_func):
    """
    Decorator to restrict view access to staff or admin users.
    
    Usage:
        @staff_required
        def my_staff_view(request):
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access Denied')
        return view_func(request, *args, **kwargs)
    
    return login_required(wrapped_view)


def instructor_required(view_func):
    """
    Decorator to restrict view access to instructors, staff, or admin.
    
    Usage:
        @instructor_required
        def my_instructor_view(request):
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not is_instructor_or_above(request.user):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access Denied')
        return view_func(request, *args, **kwargs)
    
    return login_required(wrapped_view)


def student_required(view_func):
    """
    Decorator to restrict view access to authenticated students.
    
    Usage:
        @student_required
        def my_student_view(request):
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy('aline:login'))
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


class RoleRequiredMixin:
    """
    Mixin for class-based views to check user role/permission.
    
    Usage:
        class MyView(RoleRequiredMixin, TemplateView):
            role_required = 'admin'  # or 'staff', 'instructor', 'student'
            template_name = 'my_template.html'
    """
    role_required = 'student'  # Default: any authenticated user
    
    def dispatch(self, request, *args, **kwargs):
        if not self.check_permission(request):
            messages.error(request, 'You do not have permission to access this page.')
            return HttpResponseForbidden('Access Denied')
        return super().dispatch(request, *args, **kwargs)
    
    def check_permission(self, request):
        """Check if user has the required role."""
        if not request.user.is_authenticated:
            return False
        
        if self.role_required == 'admin':
            return is_admin(request.user)
        elif self.role_required == 'staff':
            return is_staff_or_admin(request.user)
        elif self.role_required == 'instructor':
            return is_instructor_or_above(request.user)
        else:  # 'student' or default
            return True
    
    def get_context_data(self, **kwargs):
        """Add role information to context."""
        context = super().get_context_data(**kwargs)
        context['user_role'] = get_user_role(self.request.user)
        context['is_admin'] = is_admin(self.request.user)
        context['is_staff'] = is_staff_or_admin(self.request.user)
        context['is_instructor'] = is_instructor_or_above(self.request.user)
        return context
