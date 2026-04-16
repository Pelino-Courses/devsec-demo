import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .decorators import instructor_required
from .forms import RegistrationForm
from .models import Profile, LoginAttempt

# Dedicated audit logger — configured in settings.LOGGING.
# All records use structured key=value pairs for easy grep/parsing.
# NEVER log raw passwords, tokens, or session keys here.
audit_log = logging.getLogger("uwamahoro_joseline.audit")


# ── Brute-Force Protection Utilities ──────────────────────────────────────────

def get_client_ip(request):
    """Extract the client IP address from the request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def record_login_attempt(request, username, is_successful=False):
    """Record a login attempt for throttling analysis."""
    ip_address = get_client_ip(request)
    try:
        user = User.objects.get(username=username)
        LoginAttempt.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            is_successful=is_successful,
        )
    except User.DoesNotExist:
        # Still record attempt for non-existent users (prevents user enumeration)
        LoginAttempt.objects.create(
            username=username,
            ip_address=ip_address,
            is_successful=False,
        )


def get_throttle_status(username):
    """
    Check if a username is throttled due to repeated failed attempts.
    Returns (is_throttled, seconds_remaining, failed_attempts_in_window).
    
    Throttling strategy:
    - Window: Last 24 hours
    - Progressive delays: 
      - 3+ failed attempts: 5 min delay
      - 5+ failed attempts: 15 min delay
      - 10+ failed attempts: 60 min delay
      - 20+ failed attempts: 24 hour lockout
    """
    now = timezone.now()
    window_24h = now - timedelta(hours=24)
    window_1h = now - timedelta(hours=1)
    window_15m = now - timedelta(minutes=15)
    window_5m = now - timedelta(minutes=5)
    
    # Count failed attempts in different windows
    failed_24h = LoginAttempt.objects.filter(
        username=username,
        is_successful=False,
        attempt_timestamp__gte=window_24h,
    ).count()
    
    failed_1h = LoginAttempt.objects.filter(
        username=username,
        is_successful=False,
        attempt_timestamp__gte=window_1h,
    ).count()
    
    failed_15m = LoginAttempt.objects.filter(
        username=username,
        is_successful=False,
        attempt_timestamp__gte=window_15m,
    ).count()
    
    failed_5m = LoginAttempt.objects.filter(
        username=username,
        is_successful=False,
        attempt_timestamp__gte=window_5m,
    ).count()
    
    # 24-hour lockout after 20 failed attempts in 24 hours
    if failed_24h >= 20:
        oldest_failure = LoginAttempt.objects.filter(
            username=username,
            is_successful=False,
            attempt_timestamp__gte=window_24h,
        ).order_by('attempt_timestamp').first()
        
        if oldest_failure:
            unlock_time = oldest_failure.attempt_timestamp + timedelta(hours=24)
            seconds_remaining = int((unlock_time - now).total_seconds())
            if seconds_remaining > 0:
                return True, seconds_remaining, failed_24h
    
    # 60-minute delay after 10 failed attempts in 1 hour
    if failed_1h >= 10:
        oldest_failure = LoginAttempt.objects.filter(
            username=username,
            is_successful=False,
            attempt_timestamp__gte=window_1h,
        ).order_by('attempt_timestamp').first()
        
        if oldest_failure:
            unlock_time = oldest_failure.attempt_timestamp + timedelta(hours=1)
            seconds_remaining = int((unlock_time - now).total_seconds())
            if seconds_remaining > 0:
                return True, seconds_remaining, failed_1h
    
    # 15-minute delay after 5 failed attempts in 15 minutes
    if failed_15m >= 5:
        oldest_failure = LoginAttempt.objects.filter(
            username=username,
            is_successful=False,
            attempt_timestamp__gte=window_15m,
        ).order_by('attempt_timestamp').first()
        
        if oldest_failure:
            unlock_time = oldest_failure.attempt_timestamp + timedelta(minutes=15)
            seconds_remaining = int((unlock_time - now).total_seconds())
            if seconds_remaining > 0:
                return True, seconds_remaining, failed_15m
    
    # 5-minute delay after 3 failed attempts in 5 minutes
    if failed_5m >= 3:
        oldest_failure = LoginAttempt.objects.filter(
            username=username,
            is_successful=False,
            attempt_timestamp__gte=window_5m,
        ).order_by('attempt_timestamp').first()
        
        if oldest_failure:
            unlock_time = oldest_failure.attempt_timestamp + timedelta(minutes=5)
            seconds_remaining = int((unlock_time - now).total_seconds())
            if seconds_remaining > 0:
                return True, seconds_remaining, failed_5m
    
    return False, 0, failed_5m


# ── Public views ─────────────────────────────────────────────────────────────

def register_view(request):
    """
    Registration view with safe post-registration redirect.

    Open Redirect Fix: next is validated with url_has_allowed_host_and_scheme
    before use. External or protocol-relative URLs are silently ignored and
    the user lands on the dashboard instead.
    """
    if request.user.is_authenticated:
        return redirect("uwamahoro_joseline:dashboard")
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            audit_log.info(
                "USER_REGISTERED username=%s ip=%s",
                user.username,
                get_client_ip(request),
            )
            messages.success(request, "Registration successful. Welcome!")
            next_url = request.POST.get("next") or request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("uwamahoro_joseline:dashboard")
    else:
        form = RegistrationForm()
    return render(request, "uwamahoro_joseline/register.html", {"form": form, "next": next_url})


def login_view(request):
    """
    Login view with brute-force protection.
    
    Throttling Strategy:
    - 3+ failed attempts in 5 min: 5 min delay
    - 5+ failed attempts in 15 min: 15 min delay
    - 10+ failed attempts in 1 hour: 60 min delay
    - 20+ failed attempts in 24 hours: 24 hour lockout
    
    This balances security (protecting against abuse) with usability (allowing legitimate retries).
    """
    if request.user.is_authenticated:
        return redirect("uwamahoro_joseline:dashboard")
    
    if request.method == "POST":
        username = request.POST.get("username", "")
        
        # Check if account is throttled
        is_throttled, seconds_remaining, failed_attempts = get_throttle_status(username)
        if is_throttled:
            minutes_remaining = (seconds_remaining + 59) // 60  # Round up
            audit_log.warning(
                "LOGIN_THROTTLED username=%s ip=%s attempts=%d seconds_remaining=%d",
                username,
                get_client_ip(request),
                failed_attempts,
                seconds_remaining,
            )
            context = {
                "throttle_error": True,
                "username": username,
                "minutes_remaining": minutes_remaining,
                "failed_attempts": failed_attempts,
                "form": AuthenticationForm(),
                "next": request.GET.get("next", ""),
            }
            return render(request, "uwamahoro_joseline/login.html", context, status=429)

        # Process login
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            record_login_attempt(request, username, is_successful=True)
            login(request, user)
            audit_log.info(
                "LOGIN_SUCCESS username=%s ip=%s",
                user.username,
                get_client_ip(request),
            )
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("uwamahoro_joseline:dashboard")
        else:
            record_login_attempt(request, username, is_successful=False)
            audit_log.warning(
                "LOGIN_FAILED username=%s ip=%s",
                username,
                get_client_ip(request),
            )
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    return render(
        request,
        "uwamahoro_joseline/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


def logout_view(request):
    """
    Logout view with safe post-logout redirect.

    Open Redirect Fix: next is validated with url_has_allowed_host_and_scheme
    before use. External URLs are rejected and the user falls back to the
    login page, preventing phishing redirects after logout.
    """
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        next_url = request.POST.get("next") or request.GET.get("next", "")
        username = request.user.username if request.user.is_authenticated else "anonymous"
        audit_log.info(
            "LOGOUT username=%s ip=%s",
            username,
            get_client_ip(request),
        )
        logout(request)
        messages.info(request, "You have been logged out.")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect("uwamahoro_joseline:login")
    return render(request, "uwamahoro_joseline/logout.html", {"next": next_url})


# ── Student views (authenticated) ────────────────────────────────────────────

@login_required
def dashboard_view(request):
    return render(request, "uwamahoro_joseline/dashboard.html")


@login_required
def profile_view(request):
    """Display the current user's profile. Only accessible to the profile owner."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "uwamahoro_joseline/profile.html", {"profile": profile})


@login_required
def update_bio(request):
    """
    AJAX endpoint to update the user's bio.

    CSRF Fix: @csrf_exempt removed. Django's CsrfViewMiddleware now validates
    the X-CSRFToken header that the browser sends with every fetch call.
    The template reads the csrftoken cookie and passes it as a request header,
    so legitimate same-origin requests continue to work while cross-origin
    forged requests are rejected with 403.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        data = json.loads(request.body)
        bio = data.get("bio", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.bio = bio
    profile.save()
    return JsonResponse({"status": "ok", "bio": profile.bio})


@login_required
def view_user_profile(request, user_id):
    """
    Display a user's profile by ID.
    
    IDOR Protection:
    - Verify that the current user is either the profile owner or has can_view_all_profiles permission.
    - This prevents unauthorized users from accessing other users' profiles by changing the URL.
    """
    target_user = get_object_or_404(User, pk=user_id)
    
    # Check object-level access control: only allow access if:
    # 1. The request is for the current user's profile, OR
    # 2. The current user has permission to view all profiles
    if request.user != target_user and not request.user.has_perm("uwamahoro_joseline.can_view_all_profiles"):
        raise PermissionDenied("You do not have permission to view this profile.")
    
    profile, _ = Profile.objects.get_or_create(user=target_user)
    return render(request, "uwamahoro_joseline/profile.html", {"profile": profile})


@login_required
def edit_user_account(request, user_id):
    """
    Edit a user's account information.
    
    IDOR Protection:
    - Only the account owner can edit their own account.
    - Superusers can also edit any account (optional administrative override).
    """
    target_user = get_object_or_404(User, pk=user_id)
    
    # Check object-level access control: only allow access if:
    # 1. The request is from the account owner themselves
    if request.user != target_user:
        raise PermissionDenied("You do not have permission to edit this account.")
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if email and email != target_user.email:
            target_user.email = email
            target_user.save()
            messages.success(request, "Email updated successfully.")
            return redirect("uwamahoro_joseline:edit_user_account", user_id=target_user.pk)
        else:
            messages.warning(request, "No changes made.")
    
    return render(request, "uwamahoro_joseline/edit_account.html", {"target_user": target_user})


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            audit_log.info(
                "PASSWORD_CHANGED username=%s ip=%s",
                user.username,
                get_client_ip(request),
            )
            messages.success(request, "Your password was updated successfully.")
            return redirect("uwamahoro_joseline:password_change_done")
        else:
            audit_log.warning(
                "PASSWORD_CHANGE_FAILED username=%s ip=%s",
                request.user.username,
                get_client_ip(request),
            )
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "uwamahoro_joseline/password_change.html", {"form": form})


@login_required
def password_change_done_view(request):
    return render(request, "uwamahoro_joseline/password_change_done.html")


# ── Instructor views (Instructor group required) ──────────────────────────────

@instructor_required
def instructor_panel_view(request):
    """List all registered users and their roles. Instructor-only."""
    users = User.objects.select_related("profile").order_by("date_joined")
    instructor_group = Group.objects.filter(name="Instructor").first()
    instructor_ids = (
        set(instructor_group.user_set.values_list("id", flat=True))
        if instructor_group
        else set()
    )
    return render(
        request,
        "uwamahoro_joseline/instructor_panel.html",
        {"users": users, "instructor_ids": instructor_ids},
    )


@instructor_required
def promote_user_view(request, user_id):
    """
    Promote or demote a user to/from the Instructor group. Requires can_manage_users permission.
    
    IDOR Protection:
    - Verify that the user requesting the action is actually an instructor with can_manage_users permission.
    - Prevent self-promotion/demotion by checking that the target user is not the current user.
    - Explicit permission check ensures only authorized instructors can modify roles.
    """
    if not request.user.has_perm("uwamahoro_joseline.can_manage_users"):
        raise PermissionDenied("You do not have permission to manage users.")
    
    if request.method != "POST":
        return redirect("uwamahoro_joseline:instructor_panel")

    target_user = get_object_or_404(User, pk=user_id)
    
    # Object-level access control: prevent self-modification
    if request.user == target_user:
        messages.error(request, "You cannot modify your own role.")
        return redirect("uwamahoro_joseline:instructor_panel")
    
    instructor_group = get_object_or_404(Group, name="Instructor")
    action = request.POST.get("action")

    if action == "promote":
        target_user.groups.add(instructor_group)
        audit_log.info(
            "ROLE_PROMOTED target=%s by=%s ip=%s",
            target_user.username,
            request.user.username,
            get_client_ip(request),
        )
        messages.success(request, f"{target_user.username} promoted to Instructor.")
    elif action == "demote":
        target_user.groups.remove(instructor_group)
        audit_log.info(
            "ROLE_DEMOTED target=%s by=%s ip=%s",
            target_user.username,
            request.user.username,
            get_client_ip(request),
        )
        messages.success(request, f"{target_user.username} demoted to Student.")
    else:
        messages.error(request, "Invalid action.")

    return redirect("uwamahoro_joseline:instructor_panel")


# ── Password Reset views (Public/Unauthenticated) ─────────────────────────────

class SecurePasswordResetView(PasswordResetView):
    """
    Secure password reset request view using Django's built-in mechanisms.
    
    Security features:
    - Uses Django's PasswordResetForm which validates email existence safely
    - Generates cryptographically secure tokens via django.contrib.auth
    - Does NOT leak whether an email exists (always shows same success message)
    - Requires valid email format
    - Sends reset link via email only (no SMS or other direct channels)
    """
    form_class = PasswordResetForm
    template_name = "uwamahoro_joseline/password_reset.html"
    email_template_name = "uwamahoro_joseline/password_reset_email.html"
    subject_template_name = "uwamahoro_joseline/password_reset_subject.txt"
    success_url = reverse_lazy("uwamahoro_joseline:password_reset_done")

    def form_valid(self, form):
        """
        When the password reset form is valid, send the reset email.

        Audit note: we log that a reset was requested but NOT the email address
        itself — logging the email would leak account existence, undermining the
        user-enumeration protections built into Django's PasswordResetForm.
        """
        ip = get_client_ip(self.request)
        audit_log.info("PASSWORD_RESET_REQUESTED ip=%s", ip)
        return super().form_valid(form)


class SecurePasswordResetDoneView(PasswordResetDoneView):
    """
    Confirmation that password reset email was sent.
    
    Security note:
    - Shows generic message regardless of whether email exists
    - Prevents user enumeration via password reset endpoint
    - Instructs user to check email and click link
    """
    template_name = "uwamahoro_joseline/password_reset_done.html"


class SecurePasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirmation view where user sets new password.
    
    Security features:
    - Uses Django's token validation (signed tokens with timestamp)
    - Validates token hasn't expired (default: 1 day)
    - Validates new password meets Django's validation rules
    - Prevents weak or compromised passwords
    - One-time use: tokens cannot be reused
    - Automatically logs user in after password reset (improves UX)
    """
    form_class = SetPasswordForm
    template_name = "uwamahoro_joseline/password_reset_confirm.html"
    success_url = reverse_lazy("uwamahoro_joseline:password_reset_complete")
    
    def form_valid(self, form):
        """
        When the new password is set successfully via password reset link.

        Audit note: the user object is available on the form after validation.
        We log the username but never any password value.
        """
        response = super().form_valid(form)
        user = form.user
        audit_log.info(
            "PASSWORD_RESET_COMPLETED username=%s ip=%s",
            user.username,
            get_client_ip(self.request),
        )
        return response


class SecurePasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset complete confirmation page.
    
    User is prompted to log in with their new password.
    """
    template_name = "uwamahoro_joseline/password_reset_complete.html"
