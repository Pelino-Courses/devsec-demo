from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'You must be logged in to access this page.')
                return redirect('login')
            try:
                user_profile = request.user.userprofile
                if user_profile.role == required_role or user_profile.role == 'admin':
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('profile')
        return wrapper
    return decorator


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        try:
            user_profile = request.user.userprofile
            if user_profile.role == 'admin':
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        messages.error(request, 'Admin access required.')
        return redirect('profile')
    return wrapper


def editor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        try:
            user_profile = request.user.userprofile
            if user_profile.role in ['editor', 'admin']:
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        messages.error(request, 'Editor access required.')
        return redirect('profile')
    return wrapper
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'You must be logged in to access this page.')
                return redirect('login')
            try:
                user_profile = request.user.userprofile
                if user_profile.role == required_role or user_profile.role == 'admin':
                    return view_func(request, *args, **kwargs)
            except Exception:        # ✅ line 26 fixed
                pass
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
        return wrapper
    return decorator


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        try:
            user_profile = request.user.userprofile
            if user_profile.role == 'admin':
                return view_func(request, *args, **kwargs)
        except Exception:            # ✅ line 49 fixed
            pass
        messages.error(request, 'Admin access required.')
        return redirect('home')
    return wrapper


def editor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        try:
            user_profile = request.user.userprofile
            if user_profile.role in ['editor', 'admin']:
                return view_func(request, *args, **kwargs)
        except Exception:            # ✅ line 70 fixed
            pass
        messages.error(request, 'Editor access required.')
        return redirect('home')
    return wrapper