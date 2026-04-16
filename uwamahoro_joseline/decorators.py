"""
Custom decorators for role-based access control.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def instructor_required(view_func):
    """
    Decorator to restrict views to instructors only.
    
    Requires user to be logged in and a member of the 'Instructor' group.
    Raises PermissionDenied if user is not an instructor.
    """
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.groups.filter(name='Instructor').exists():
            return view_func(request, *args, **kwargs)
        else:
            raise PermissionDenied("You must be an instructor to access this page.")
    
    return wrapper
