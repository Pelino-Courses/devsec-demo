from django.http import HttpResponseForbidden
from functools import wraps
from .models import Profile


def role_required(*roles):
    """
    Decorator that restricts access to users with specific roles.
    Usage: @role_required('instructor', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.shortcuts import redirect
                return redirect('irumvajeanmarie:login')
            try:
                profile = Profile.objects.get(user=request.user)
                if profile.role not in roles:
                    return HttpResponseForbidden(
                        "Access denied: You do not have permission to view this page."
                    )
            except Profile.DoesNotExist:
                return HttpResponseForbidden(
                    "Access denied: No profile found."
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def instructor_required(view_func):
    """Restricts access to instructors and admins only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('irumvajeanmarie:login')
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role not in [Profile.ROLE_INSTRUCTOR, Profile.ROLE_ADMIN]:
                return HttpResponseForbidden(
                    "Access denied: Instructor or Admin role required."
                )
        except Profile.DoesNotExist:
            return HttpResponseForbidden("Access denied: No profile found.")
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Restricts access to admins only."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('irumvajeanmarie:login')
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role != Profile.ROLE_ADMIN:
                return HttpResponseForbidden(
                    "Access denied: Admin role required."
                )
        except Profile.DoesNotExist:
            return HttpResponseForbidden("Access denied: No profile found.")
        return view_func(request, *args, **kwargs)
    return wrapper