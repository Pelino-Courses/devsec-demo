import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .forms import RegistrationForm, LoginForm, PasswordChangeForm, UserProfileForm
from .models import UserProfile, LoginAttempt

# ---------------------------------------------------------------------------
# Brute-force protection constants
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS = 5       # failures allowed before lockout triggers
LOCKOUT_WINDOW_MINUTES = 15  # rolling window that failures are counted within


def _get_client_ip(request):
    """Return the client's IP address from the request."""
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _safe_next_url(request, fallback='hirwafab:dashboard'):
    """
    Return a validated redirect target from the next GET or POST parameter.

    Uses Django's url_has_allowed_host_and_scheme to ensure the target is:
    - a relative path (no scheme → no external domain possible), OR
    - an absolute URL whose host matches the current request host.

    Any value that fails this check is discarded and the fallback named URL
    is returned instead. This prevents open redirect attacks where an attacker
    supplies next=https://evil.com to silently forward the victim after login.
    """
    next_url = request.POST.get('next', request.GET.get('next', ''))
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def _lockout_info(username, ip_address):
    """
    Check whether a username or IP address is currently locked out.

    Counts failed LoginAttempt records within the rolling LOCKOUT_WINDOW_MINUTES.
    If either the per-account or per-IP count reaches MAX_LOGIN_ATTEMPTS the
    login is blocked until the most recent triggering failure ages out of the
    window.

    Returns:
        (is_locked: bool, minutes_remaining: int)
    """
    window_start = timezone.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

    checks = [
        LoginAttempt.objects.filter(username__iexact=username, timestamp__gte=window_start),
        LoginAttempt.objects.filter(ip_address=ip_address, timestamp__gte=window_start),
    ]

    for attempts_qs in checks:
        if attempts_qs.count() >= MAX_LOGIN_ATTEMPTS:
            latest = attempts_qs.latest('timestamp')
            unlock_at = latest.timestamp + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
            now = timezone.now()
            if now < unlock_at:
                seconds_left = int((unlock_at - now).total_seconds())
                minutes_left = max(1, (seconds_left + 59) // 60)
                return True, minutes_left

    return False, 0


@require_http_methods(["GET", "POST"])
@csrf_protect
def register(request):
    """
    Handle user registration.
    
    GET: Display registration form
    POST: Process registration and create new user account
    """
    if request.user.is_authenticated:
        return redirect('hirwafab:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-assign user to 'students' group for RBAC
            try:
                students_group = Group.objects.get(name='students')
                user.groups.add(students_group)
            except Group.DoesNotExist:
                pass  # Group will be created via management command
            
            messages.success(
                request,
                f'Account created successfully! Welcome {user.username}. You can now log in.'
            )
            return redirect('hirwafab:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'hirwafab/register.html', context)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    Handle user login with brute-force protection.

    Protection model (hybrid account + IP):
    - Every failed credential check records a LoginAttempt row.
    - Before authenticating, both the submitted username and the client IP are
      checked against the rolling LOCKOUT_WINDOW_MINUTES window.
    - If either reaches MAX_LOGIN_ATTEMPTS failures the form is blocked and the
      remaining cooldown is shown to the user.
    - A successful login clears all LoginAttempt rows for that username so a
      legitimate user is not penalised after recovering their password.

    GET: Display login form
    POST: Check lockout → authenticate → record failure or clear & redirect
    """
    if request.user.is_authenticated:
        return redirect('hirwafab:dashboard')

    ip_address = _get_client_ip(request)
    extra_context = {}

    # Validate next before use — rejects external hosts and bare-scheme URLs.
    next_url = _safe_next_url(request, fallback='hirwafab:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')

            # --- lockout gate ---
            is_locked, minutes_remaining = _lockout_info(username, ip_address)
            if is_locked:
                noun = 'minute' if minutes_remaining == 1 else 'minutes'
                messages.error(
                    request,
                    f'Too many failed login attempts. '
                    f'Please try again in {minutes_remaining} {noun}.',
                )
                extra_context['locked_out'] = True
                extra_context['minutes_remaining'] = minutes_remaining
            else:
                password = form.cleaned_data.get('password')
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    # Clear failure history on successful login
                    LoginAttempt.objects.filter(username__iexact=username).delete()
                    login(request, user)
                    # Ensure user is in students group — handles accounts created
                    # before RBAC migration ran.
                    if not user.groups.exists():
                        try:
                            user.groups.add(Group.objects.get(name='students'))
                        except Group.DoesNotExist:
                            pass
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect(next_url)
                else:
                    LoginAttempt.objects.create(username=username, ip_address=ip_address)
                    messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    context = {'form': form, 'next': next_url, **extra_context}
    return render(request, 'hirwafab/login.html', context)


@login_required(login_url='hirwafab:login')
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Handle user logout.
    Clears the user session and redirects to login page.
    """
    if request.method == 'POST':
        next_url = _safe_next_url(request, fallback='hirwafab:login')
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect(next_url)

    return render(request, 'hirwafab/logout_confirm.html')


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_dashboard', raise_exception=True)
def dashboard(request):
    """
    Protected dashboard page - requires authentication and view_dashboard permission.
    Displays user's profile information and welcome message.
    """
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'hirwafab/dashboard.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.change_own_password', raise_exception=True)
@require_http_methods(["GET", "POST"])
def change_password(request):
    """
    Handle password change for authenticated users.
    Requires change_own_password permission.
    
    GET: Display password change form
    POST: Process password change with validation
    """
    # Object-level ownership check: password changes must only ever apply to
    # the currently authenticated user — never to a user resolved from
    # external input.
    if not request.user.is_authenticated:
        raise PermissionDenied

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('hirwafab:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = PasswordChangeForm(request.user)

    context = {'form': form}
    return render(request, 'hirwafab/change_password.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_own_profile', raise_exception=True)
@require_http_methods(["GET", "POST"])
def profile(request):
    """
    Handle user profile view and updates.
    Requires view_own_profile permission.
    
    GET: Display user profile
    POST: Update profile information
    """
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    # Object-level ownership check: the profile being edited must belong to
    # the currently authenticated user. This prevents IDOR if the profile
    # object is ever resolved through a different path.
    if user_profile.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('hirwafab:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=user_profile)

    context = {
        'form': form,
        'profile': user_profile,
    }
    return render(request, 'hirwafab/profile.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_user_directory', raise_exception=True)
def user_directory(request):
    """
    Public user directory - shows all users with basic information.
    Requires view_user_directory permission (student and above).
    """
    users = UserProfile.objects.all().select_related('user')
    
    context = {
        'users': users,
        'is_public_view': True,
    }
    return render(request, 'hirwafab/user_directory.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_all_profiles', raise_exception=True)
def user_directory_full(request):
    """
    Full user directory with detailed information - instructor/admin only.
    Requires view_all_profiles permission (instructors and above).
    Shows email, bio, avatar, and registration date.
    """
    users = UserProfile.objects.all().select_related('user')
    
    context = {
        'users': users,
        'is_full_view': True,
    }
    return render(request, 'hirwafab/user_directory_full.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_all_profiles', raise_exception=True)
def view_user_profile(request, user_id):
    """
    View another user's profile - instructor/admin only.
    Requires view_all_profiles permission.
    Can only view other users' full profiles, not their own (use profile() for that).
    """
    # Redirect to own profile page when requesting own user_id
    if request.user.id == user_id:
        return redirect('hirwafab:profile')

    user_profile = get_object_or_404(UserProfile, user_id=user_id)

    # Object-level check: even after the role-level @permission_required above,
    # explicitly verify the requesting user is authorised to view this specific
    # profile object. Only instructors (view_all_profiles) and superusers may
    # view another user's full profile.
    if not (request.user.has_perm('hirwafab.view_all_profiles') or request.user.is_superuser):
        raise PermissionDenied

    context = {
        'profile': user_profile,
        'is_other_profile': True,
    }
    return render(request, 'hirwafab/view_user_profile.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_user_activity', raise_exception=True)
def user_activity(request):
    """
    View user activity and statistics - instructor only.
    Requires view_user_activity permission.
    Shows registration dates, last login info, and activity summary.
    """
    users = UserProfile.objects.all().select_related('user').order_by('-created_at')
    
    # Calculate statistics
    total_users = users.count()
    recent_registrations = users[:10]  # Last 10 registered
    
    context = {
        'users': users,
        'total_users': total_users,
        'recent_registrations': recent_registrations,
    }
    return render(request, 'hirwafab/user_activity.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.download_reports', raise_exception=True)
def reports(request):
    """
    Generate and download user reports - instructor only.
    Requires download_reports permission.
    Provides export of user data in various formats.
    """
    users = UserProfile.objects.all().select_related('user')
    user_data = []
    
    for profile in users:
        user_data.append({
            'username': profile.user.username,
            'email': profile.user.email,
            'first_name': profile.user.first_name,
            'last_name': profile.user.last_name,
            'registered': profile.created_at,
            'bio': profile.bio,
        })
    
    context = {
        'user_count': users.count(),
        'user_data': user_data,
    }
    return render(request, 'hirwafab/reports.html', context)


# ---------------------------------------------------------------------------
# AJAX bio update — CSRF protection enforced by CsrfViewMiddleware.
# Client must supply the X-CSRFToken header; requests without it get 403.
# ---------------------------------------------------------------------------

@login_required(login_url='hirwafab:login')
@require_http_methods(["POST"])
def ajax_bio_update(request):
    """
    AJAX endpoint to update the authenticated user's bio.

    CSRF protection is provided by CsrfViewMiddleware (active in settings).
    The calling JavaScript reads the token from the DOM and sends it as the
    X-CSRFToken request header. Requests that omit the token receive 403.
    """
    try:
        data = json.loads(request.body)
        bio = data.get('bio', '').strip()[:500]
        profile = request.user.profile
        profile.bio = bio
        profile.save(update_fields=['bio', 'updated_at'])
        return JsonResponse({'status': 'ok', 'bio': bio})
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
