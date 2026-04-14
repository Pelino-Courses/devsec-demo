from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .roles import is_instructor, is_admin


def instructor_required(view_func):
    """Allow only instructors and admins."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('jeanclaudeirumva:login')
        if not (is_instructor(request.user) or is_admin(request.user)):
            messages.error(request, "Access denied. Instructor role required.")
            return redirect('jeanclaudeirumva:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Allow only admins."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('jeanclaudeirumva:login')
        if not is_admin(request.user):
            messages.error(request, "Access denied. Admin role required.")
            return redirect('jeanclaudeirumva:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
    