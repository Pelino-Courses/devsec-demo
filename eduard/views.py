import json


from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .audit import (
    log_registration,
    log_login_success,
    log_login_failure,
    log_account_locked,
    log_logout,
    log_password_change,
    log_password_reset_request,
)
from .decorators import instructor_required

from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

from .forms import RegistrationForm, LoginForm, UserPasswordChangeForm, BioForm, ProfileForm
from .models import LoginAttempt, UserProfile

def _is_safe_url(url, request):
    """
    Return True only if the redirect target is safe to use.
    Rejects external hosts and dangerous schemes such as javascript://.
    """
    if not url:
        return False
    return url_has_allowed_host_and_scheme(
        url=url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    )


def register(request):
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_registration(request, user.username)
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('eduard:dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'eduard/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        attempt, _ = LoginAttempt.objects.get_or_create(username=username)

        if attempt.is_locked():
            log_account_locked(request, username)
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
            log_login_success(request, user.username)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            if _is_safe_url(next_url, request):
                return redirect(next_url)
            return redirect('eduard:dashboard')
        else:
            attempt.record_failure()
            log_login_failure(request, username, attempt.failed_attempts)
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
        username = request.user.username
        logout(request)
        log_logout(request, username)
        messages.info(request, 'You have been logged out.')
    return redirect('eduard:login')


@login_required
def dashboard(request):
    return render(request, 'eduard/dashboard.html')


@login_required
def profile(request):
    """
    Display and update the current user's profile including bio and avatar.

    Upload security: ProfileForm.clean_avatar() runs validate_avatar()
    which checks extension, file size, and magic bytes before saving.
    The filename is randomised by avatar_upload_path to prevent
    path traversal attacks.
    """
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('eduard:profile')
    else:
        form = ProfileForm(instance=user_profile)

    return render(request, 'eduard/profile.html', {
        'profile_user': request.user,
        'user_profile': user_profile,
        'bio_form': form,
    })
    """
    Display and update the current user's profile including their bio.

    XSS fix: the bio is rendered in the template using {{ profile.bio }}
    with no |safe filter. Django auto-escaping converts any HTML
    characters to their safe entity equivalents before sending them
    to the browser, so stored script tags are displayed as text, not
    executed.
    """
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = BioForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bio updated successfully.')
            return redirect('eduard:profile')
    else:
        form = BioForm(instance=user_profile)

    return render(request, 'eduard/profile.html', {
        'profile_user': request.user,
        'user_profile': user_profile,
        'bio_form': form,
    })

@login_required
def profile_by_id(request, user_id):
    is_privileged = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.groups.filter(name='Instructor').exists()
    )
    if not is_privileged:
        raise PermissionDenied
    profile_user = get_object_or_404(User, id=user_id)
    user_profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    return render(request, 'eduard/profile.html', {
        'profile_user': profile_user,
        'user_profile': user_profile,
        'bio_form': None,
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_password_change(request, request.user.username)
            messages.success(request, 'Your password was updated successfully.')
            return redirect('eduard:profile')
    else:
        form = UserPasswordChangeForm(request.user)

    return render(request, 'eduard/change_password.html', {'form': form})


@login_required
def update_display_name(request):
    """
    AJAX endpoint for updating display name.
    CSRF-safe: uses X-CSRFToken header pattern, no @csrf_exempt.
    """
    if request.method == 'POST':
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


@instructor_required
def instructor_dashboard(request):
    users = User.objects.all().order_by('date_joined')
    return render(request, 'eduard/instructor_dashboard.html', {'users': users})


class AuditedPasswordResetView(PasswordResetView):
    """
    Extends Django's PasswordResetView to add audit logging.
    Logs the email submitted without revealing whether an account exists.
    """
    template_name = 'eduard/password_reset.html'
    email_template_name = 'eduard/password_reset_email.txt'
    subject_template_name = 'eduard/password_reset_subject.txt'
    success_url = reverse_lazy('eduard:password_reset_done')

def form_valid(self, form):
    email = form.cleaned_data.get('email', '')
    log_password_reset_request(self.request, email)
    return super().form_valid(form)


def forbidden(request, exception=None):
    return render(request, 'eduard/403.html', status=403)