from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from .models import LoginAttempt
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

from .decorators import instructor_required
from .forms import RegistrationForm, LoginForm, UserPasswordChangeForm


def register(request):
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('eduard:dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'eduard/register.html', {'form': form})


def _is_safe_url(url, request):
    """
    Return True only if the redirect target is safe to use.

    Django's url_has_allowed_host_and_scheme checks two things:
    1. The URL does not point to an external host
    2. The URL uses an allowed scheme (http/https, not javascript://)

    Any URL that fails either check is rejected and the user falls
    back to the default destination instead.
    """
    if not url:
        return False
    return url_has_allowed_host_and_scheme(
        url=url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )


def user_login(request):
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        attempt, _ = LoginAttempt.objects.get_or_create(username=username)

        if attempt.is_locked():
            minutes = attempt.seconds_until_unlock() // 60
            seconds = attempt.seconds_until_unlock() % 60
            messages.error(
                request,
                f'This account is locked due to too many failed attempts. '
                f'Please try again in {minutes}m {seconds}s or reset your password.',
            )
            return render(request, 'eduard/login.html', {'form': LoginForm(request)})

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            attempt.clear()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if _is_safe_url(next_url, request):
                return redirect(next_url)
            return redirect('eduard:dashboard')
        else:
            attempt.record_failure()
            remaining = 5 - attempt.failed_attempts
            if attempt.is_locked():
                messages.error(
                    request,
                    'Too many failed attempts. This account is locked for 15 minutes.',
                )
            else:
                messages.error(
                    request,
                    f'Invalid username or password. '
                    f'{remaining} attempt{"s" if remaining != 1 else ""} remaining before lockout.',
                )
    else:
        form = LoginForm(request)

    return render(request, 'eduard/login.html', {'form': form})


def user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('eduard:login')

@login_required
def dashboard(request):
    return render(request, 'eduard/dashboard.html')


@login_required
def profile(request):
    """
    Always serves the currently authenticated user's own profile.
    No user identifier is accepted from the URL — the identity comes
    exclusively from the session, so there is no object reference to
    manipulate.
    """
    return render(request, 'eduard/profile.html', {'profile_user': request.user})


@login_required
def profile_by_id(request, user_id):
    """
    IDOR-safe profile lookup by user ID.

    The risk: if this view simply did User.objects.get(id=user_id),
    any logged-in user could view any other user's profile by changing
    the user_id in the URL.

    The fix: only staff and instructors may look up profiles by ID.
    Normal users are raised a 403 immediately — they must use /profile/
    which always serves their own data from the session.
    """
    is_privileged = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.groups.filter(name='Instructor').exists()
    )

    if not is_privileged:
        raise PermissionDenied

    profile_user = get_object_or_404(User, id=user_id)
    return render(request, 'eduard/profile.html', {'profile_user': profile_user})


@login_required
def change_password(request):
    """
    Password change always operates on request.user — never on a URL
    parameter — so there is no object reference to manipulate here.
    """
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was updated successfully.')
            return redirect('eduard:profile')
    else:
        form = UserPasswordChangeForm(request.user)

    return render(request, 'eduard/change_password.html', {'form': form})


@instructor_required
def instructor_dashboard(request):
    """
    Accessible only to users in the Instructor group or staff/superusers.
    Normal authenticated users get a 403 Forbidden response.
    """
    users = User.objects.all().order_by('date_joined')
    return render(request, 'eduard/instructor_dashboard.html', {'users': users})


def forbidden(request, exception=None):
    """
    Custom 403 handler - renders a friendly error page.
    """
    return render(request, 'eduard/403.html', status=403)



# ---------------------------------------------------------------------------
# CSRF demonstration - insecure version (immediately replaced below)
# ---------------------------------------------------------------------------
# The view below shows what an unsafe CSRF-exempt endpoint looks like.
# It is defined here for reference only and is NOT wired to any URL.
# Decorating a state-changing endpoint with @csrf_exempt removes Django's
# CSRF check entirely, meaning any website can silently trigger this action
# on behalf of a logged-in user just by submitting a hidden form or fetch().
#
# @csrf_exempt                        # UNSAFE - do not use on POST endpoints
# @login_required
# def update_display_name_unsafe(request):
#     if request.method == 'POST':
#         name = request.POST.get('display_name', '')
#         request.user.first_name = name
#         request.user.save()
#         return JsonResponse({'status': 'ok'})
#     return JsonResponse({'error': 'method not allowed'}, status=405)
# ---------------------------------------------------------------------------


@login_required
def update_display_name(request):
    """
    AJAX endpoint that lets a user update their display name.

    CSRF fix: this endpoint does NOT use @csrf_exempt. Django's
    CsrfViewMiddleware is active globally in settings.py, so every
    POST request must include a valid CSRF token. The JavaScript
    in the profile template reads the token from the cookie using
    the standard Django pattern and sends it in the X-CSRFToken
    header, which Django accepts as equivalent to the form field.

    This means a cross-origin attacker cannot trigger this endpoint
    because they cannot read the victim's CSRF cookie from a
    different origin (same-origin policy).
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'invalid JSON'}, status=400)

        display_name = data.get('display_name', '').strip()
        if len(display_name) > 50:
            return JsonResponse({'error': 'Display name too long'}, status=400)

        request.user.first_name = display_name
        request.user.save(update_fields=['first_name'])
        return JsonResponse({'status': 'ok', 'display_name': display_name})

    return JsonResponse({'error': 'method not allowed'}, status=405)