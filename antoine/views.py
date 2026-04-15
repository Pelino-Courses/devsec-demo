from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import UserProfile, LoginHistory, PasswordChangeHistory, LoginAttempt, AuditLog
from .forms import (
    RegistrationForm, LoginForm, UserProfileForm,
    CustomPasswordChangeForm, PasswordResetRequestForm, PasswordResetForm
)
from .permissions import (
    admin_required, instructor_required, has_permission,
    get_user_role, is_admin, is_instructor, admin_can_access_object
)


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extract user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')


def log_audit_event(request, event_type, user=None, affected_user=None, 
                    severity='MEDIUM', description='', details=None):
    """
    Log security-relevant events to AuditLog.
    
    Args:
        request: Django request object (for IP and user agent)
        event_type: Event type from AuditLog.EVENT_TYPES
        user: User who triggered the event (defaults to request.user)
        affected_user: User affected by the event (may differ for admin actions)
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
        description: Human-readable description of the event
        details: Dict with structured data (NO passwords or secrets)
    """
    if details is None:
        details = {}
    
    # Default user is the current request user
    if user is None and request.user.is_authenticated:
        user = request.user
    
    AuditLog.objects.create(
        user=user,
        affected_user=affected_user,
        event_type=event_type,
        severity=severity,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        description=description,
        details=details
    )


def get_safe_redirect_url(next_url, request, fallback_url_name='antoine:dashboard'):
    """
    Safely handle redirect URLs to prevent open redirect attacks.
    
    Security:
    - Only allows relative internal URLs (starting with /)
    - Validates URL is on allowed hosts (blocks //attacker.com)
    - Rejects absolute external URLs
    - Returns fallback if redirect is unsafe
    
    Args:
        next_url: URL to redirect to (from request parameter)
        request: Django request object (for host validation)
        fallback_url_name: Django URL name to use as fallback
    
    Returns:
        Safe redirect destination (URL name or relative path)
    """
    # Check if next_url looks like a URL name (no slashes)
    # URL names like 'antoine:dashboard' should fallback to default
    if not next_url or not isinstance(next_url, str):
        return fallback_url_name
    
    # Only allow relative URLs (starting with /)
    if not next_url.startswith('/'):
        return fallback_url_name
    
    # Validate the URL is safe (not protocol-relative, not external, etc.)
    # url_has_allowed_host_and_scheme checks if URL doesn't try to redirect externally
    if url_has_allowed_host_and_scheme(url=next_url, allowed_hosts=None):
        return next_url
    
    # If URL doesn't pass validation, use safe default
    return fallback_url_name


@require_http_methods(["GET", "POST"])
@csrf_protect
def register(request):
    """
    User registration view.
    Handles both GET (display form) and POST (process registration).
    """
    if request.user.is_authenticated:
        return redirect('antoine:dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Log registration
                log_audit_event(
                    request,
                    'REGISTRATION',
                    user=user,
                    affected_user=user,
                    severity='LOW',
                    description=f'User {user.username} registered a new account',
                    details={'username': user.username, 'email': user.email}
                )
                
                messages.success(
                    request,
                    f'Account created successfully! Welcome, {user.username}. Please log in.'
                )
                return redirect('antoine:login')
            except IntegrityError as e:
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegistrationForm()
    
    return render(request, 'antoine/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    User login view with brute-force attack protection.
    
    Security measures:
    - Tracks failed login attempts per account
    - Implements progressive cooldowns after 5 failures:
      * 5-9 failures: 30 second lockout
      * 10-14 failures: 1 minute lockout
      * 15-19 failures: 5 minute lockout
      * 20+ failures: 15 minute lockout
    - Shows generic error message (user enumeration prevention)
    - Logs all attempts to LoginHistory for audit trail
    """
    if request.user.is_authenticated:
        return redirect('antoine:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            
            # Look up user first (before authentication)
            try:
                user_obj = User.objects.get(username=username)
                login_attempt, _ = LoginAttempt.objects.get_or_create(user=user_obj)
                
                # Check if account is locked
                if login_attempt.is_locked:
                    log_audit_event(
                        request,
                        'LOGIN_FAILURE',
                        user=user_obj,
                        affected_user=user_obj,
                        severity='HIGH',
                        description=f'Login attempt on manually locked account {user_obj.username}',
                        details={'reason': 'account_manually_locked'}
                    )
                    messages.error(
                        request,
                        'This account has been manually locked. Please contact support.'
                    )
                    return render(request, 'antoine/login.html', {'form': form})
                
                # Check if temporarily locked due to failed attempts
                if login_attempt.is_temporarily_locked():
                    cooldown = login_attempt.get_cooldown_seconds()
                    log_audit_event(
                        request,
                        'LOGIN_FAILURE',
                        user=user_obj,
                        affected_user=user_obj,
                        severity='MEDIUM',
                        description=f'Login attempt on temporarily locked account {user_obj.username} due to brute-force protection',
                        details={'reason': 'temporary_lockout', 'failed_attempts': login_attempt.failed_attempts}
                    )
                    messages.error(
                        request,
                        f'Too many failed login attempts. '
                        f'Please try again in {cooldown} seconds.'
                    )
                    return render(request, 'antoine/login.html', {'form': form})
                
            except User.DoesNotExist:
                # User doesn't exist - don't reveal this
                user_obj = None
                login_attempt = None
            
            # Attempt authentication
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Successful login
                login(request, user)
                
                # Set session timeout
                if remember_me:
                    request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                else:
                    request.session.set_expiry(0)  # Browser close
                
                # Log successful login to AuditLog
                log_audit_event(
                    request,
                    'LOGIN_SUCCESS',
                    user=user,
                    affected_user=user,
                    severity='LOW',
                    description=f'User {user.username} logged in successfully',
                    details={'username': user.username, 'session_expiry': 'remember_me' if remember_me else 'browser_close'}
                )
                
                # Log successful login to LoginHistory (existing tracking)
                LoginHistory.objects.create(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
                
                # Reset failed attempts
                if login_attempt:
                    login_attempt.reset_attempts()
                
                # Update last login IP
                try:
                    profile = user.antoine_profile
                    profile.last_login_ip = ip_address
                    profile.save()
                except UserProfile.DoesNotExist:
                    UserProfile.objects.create(user=user, last_login_ip=ip_address)
                
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Redirect to next URL or dashboard (with open redirect protection)
                next_url = request.GET.get('next')
                safe_redirect = get_safe_redirect_url(next_url, request, 'antoine:dashboard')
                return redirect(safe_redirect)
            else:
                # Failed login - track the attempt
                if user_obj:
                    login_attempt.increment_failed_attempts()
                    
                    # Log failed login to AuditLog
                    log_audit_event(
                        request,
                        'LOGIN_FAILURE',
                        user=user_obj,
                        affected_user=user_obj,
                        severity='MEDIUM',
                        description=f'Failed login attempt for user {user_obj.username} (attempt #{login_attempt.failed_attempts})',
                        details={'reason': 'invalid_password', 'attempt_number': login_attempt.failed_attempts}
                    )
                    
                    # Log failed login to LoginHistory (existing tracking)
                    LoginHistory.objects.create(
                        user=user_obj,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        failure_reason='Invalid password'
                    )
                
                # Generic error message (user enumeration prevention)
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'antoine/login.html', {'form': form})


@login_required(login_url='antoine:login')
@require_http_methods(["POST"])  # POST-only to prevent CSRF via <img> or <a> tags
@csrf_protect  # Validate CSRF token
def logout_view(request):
    """
    User logout view.
    Clears session and redirects to home page.
    
    Security:
    - POST-only: Prevents CSRF via <img src> or <a href> tags
    - CSRF token required: Ensures logout is intentional user action
    """
    user = request.user
    
    # Log logout
    log_audit_event(
        request,
        'LOGOUT',
        user=user,
        affected_user=user,
        severity='LOW',
        description=f'User {user.username} logged out',
        details={'username': user.username}
    )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('antoine:login')


@login_required(login_url='antoine:login')
def dashboard(request):
    """
    Dashboard/home view for authenticated users.
    Shows user statistics and options.
    """
    try:
        profile = request.user.antoine_profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    recent_logins = LoginHistory.objects.filter(user=request.user)[:5]
    total_logins = LoginHistory.objects.filter(user=request.user, success=True).count()
    
    context = {
        'profile': profile,
        'recent_logins': recent_logins,
        'total_logins': total_logins,
    }
    
    return render(request, 'antoine/dashboard.html', context)


@login_required(login_url='antoine:login')
@require_http_methods(["GET", "POST"])
@login_required(login_url='antoine:login')
@csrf_protect  # Validate CSRF token for profile updates
def profile_view(request):
    """
    User profile view and update.
    Allows users to update their profile information.
    
    IDOR Protection: Accesses request.user.antoine_profile (no user_id parameter),
    so users can only view/edit their own profile.
    
    CSRF Protection: @csrf_protect validates CSRF token on POST requests,
    preventing unauthorized profile modifications via cross-site requests.
    """
    try:
        profile = request.user.antoine_profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('antoine:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'antoine/profile.html', context)


@login_required(login_url='antoine:login')
@require_http_methods(["GET", "POST"])
@csrf_protect  # Validate CSRF token for password changes
def change_password(request):
    """
    Change password view.
    Allows authenticated users to change their password.
    
    IDOR Protection: Uses request.user (no user_id parameter),
    so each user can only change their own password.
    
    CSRF Protection: @csrf_protect validates CSRF token on POST requests,
    preventing unauthorized password changes via cross-site requests.
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log password change
            ip_address = get_client_ip(request)
            PasswordChangeHistory.objects.create(
                user=user,
                ip_address=ip_address
            )
            
            # Log to AuditLog
            log_audit_event(
                request,
                'PASSWORD_CHANGE',
                user=user,
                affected_user=user,
                severity='HIGH',
                description=f'User {user.username} changed their password',
                details={'username': user.username}
            )
            
            # Update session to prevent logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Password changed successfully!')
            return redirect('antoine:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'antoine/change_password.html', {'form': form})


@login_required(login_url='antoine:login')
def login_history(request):
    """
    View user's login history.
    Shows all login attempts (successful and failed).
    
    IDOR Protection: Filters LoginHistory by request.user (no user_id parameter),
    so each user only sees their own login history.
    """
    logins = LoginHistory.objects.filter(user=request.user).order_by('-login_time')[:50]
    
    context = {
        'logins': logins,
    }
    
    return render(request, 'antoine/login_history.html', context)


@login_required(login_url='antoine:login')
def public_profile(request, user_id):
    """
    View other users' public profiles.
    Only shows basic public information, not sensitive data.
    
    IDOR Protection: Users can view any public profile (not account-specific),
    but only public data is shown. Sensitive data (email, IP, etc) is excluded.
    get_object_or_404 returns 404 for non-existent users (not 403).
    """
    user = get_object_or_404(User, pk=user_id)
    
    try:
        profile = user.antoine_profile
    except UserProfile.DoesNotExist:
        profile = None
    
    context = {
        'target_user': user,
        'profile': profile,
    }
    
    return render(request, 'antoine/public_profile.html', context)


@login_required(login_url='antoine:login')
@instructor_required
def manage_users(request):
    """
    Admin/Instructor view to manage all users.
    Requires instructor or admin role.
    Shows all users with options to view/reset passwords.
    """
    users = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    
    context = {
        'users': users,
        'is_admin': is_admin(request.user),
        'is_instructor': is_instructor(request.user),
    }
    
    return render(request, 'antoine/manage_users.html', context)


@login_required(login_url='antoine:login')
@instructor_required
def audit_logs(request):
    """
    Admin/Instructor view to see all login audit logs.
    Requires instructor or admin role.
    """
    logins = LoginHistory.objects.all().select_related('user').order_by('-login_time')[:100]
    password_changes = PasswordChangeHistory.objects.all().select_related('user').order_by('-changed_at')[:50]
    
    context = {
        'logins': logins,
        'password_changes': password_changes,
        'is_admin': is_admin(request.user),
    }
    
    return render(request, 'antoine/audit_logs.html', context)


@login_required(login_url='antoine:login')
@admin_required
@admin_can_access_object('user_id')
@require_http_methods(["GET", "POST"])  # Explicit HTTP method validation
@csrf_protect  # Validate CSRF token to prevent unauthorized password resets
def reset_user_password(request, user_id):
    """
    Admin-only view to reset another user's password.
    Generates a temporary password and logs the action.
    
    IDOR Protection: @admin_can_access_object ensures the user_id exists
    and prevents enumeration attacks via different error messages.
    
    CSRF Protection: @csrf_protect validates CSRF token on POST requests.
    Prevents attackers from tricking admins into resetting passwords
    via cross-site request forgery.
    """
    target_user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        # Generate temporary password
        import secrets
        import string
        chars = string.ascii_letters + string.digits + string.punctuation
        temp_password = ''.join(secrets.choice(chars) for _ in range(12))
        
        target_user.set_password(temp_password)
        target_user.save()
        
        # Log password reset by admin
        ip_address = get_client_ip(request)
        PasswordChangeHistory.objects.create(
            user=target_user,
            ip_address=ip_address
        )
        
        # Log admin password reset action
        log_audit_event(
            request,
            'ADMIN_ACTION',
            user=request.user,
            affected_user=target_user,
            severity='CRITICAL',
            description=f'Admin {request.user.username} reset password for user {target_user.username}',
            details={
                'admin_username': request.user.username,
                'target_username': target_user.username,
                'action': 'password_reset',
                'temp_password_generated': True
            }
        )
        
        messages.success(
            request,
            f'Password reset for {target_user.username}. '
            f'Temporary password: {temp_password} '
            f'(User should change this on next login)'
        )
        return redirect('antoine:manage_users')
    
    context = {
        'target_user': target_user,
    }
    
    return render(request, 'antoine/reset_user_password.html', context)


# Password Reset Flow (Self-Service)

@require_http_methods(["GET", "POST"])
@csrf_protect
def password_reset_request(request):
    """
    Password reset request view.
    User enters their email and receives a reset link if account exists.
    
    Security:
    - Uses same message for all cases (user exists or not) to prevent enumeration
    - Sends email with secure Django token (default_token_generator)
    - Token expires after PASSWORD_RESET_TIMEOUT (default: 1 week)
    """
    if request.user.is_authenticated:
        return redirect('antoine:dashboard')
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            
            # Try to find user by email
            try:
                user = User.objects.get(email=email)
                
                # Generate secure token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Build reset link
                reset_link = request.build_absolute_uri(
                    f'/password-reset-confirm/{uid}/{token}/'
                )
                
                # Send email
                subject = 'Password Reset Request'
                html_message = render_to_string(
                    'antoine/password_reset_email.html',
                    {
                        'user': user,
                        'reset_link': reset_link,
                        'token_expiry_days': 7,  # Django default
                    }
                )
                
                send_mail(
                    subject,
                    f'Visit this link to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                
                # Log password reset request
                log_audit_event(
                    request,
                    'PASSWORD_RESET_REQUEST',
                    user=user,
                    affected_user=user,
                    severity='MEDIUM',
                    description=f'User {user.username} (email: {user.email}) requested a password reset',
                    details={'email': user.email, 'username': user.username}
                )
                
            except User.DoesNotExist:
                # User enumeration prevention: same message, but log attempt for security
                log_audit_event(
                    request,
                    'PASSWORD_RESET_REQUEST',
                    user=None,
                    affected_user=None,
                    severity='LOW',
                    description=f'Password reset requested for non-existent email: {email}',
                    details={'email': email, 'user_found': False}
                )
            
            # Always show success message (don't leak if email exists)
            messages.success(
                request,
                'If an account with that email exists, '
                'a password reset link has been sent. '
                'Check your email (including spam folder).'
            )
            return redirect('antoine:password_reset_done')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'antoine/password_reset_request.html', {'form': form})


def password_reset_done(request):
    """
    Password reset request done view.
    Shows confirmation message that email was sent.
    """
    return render(request, 'antoine/password_reset_done.html')


@require_http_methods(["GET", "POST"])
@csrf_protect
def password_reset_confirm(request, uidb64, token):
    """
    Password reset confirm view.
    User enters new password after validating reset token.
    
    Security:
    - Validates token using Django's default_token_generator
    - Token includes user ID and is time-bound
    - Expired tokens show generic "invalid link" message
    - Prevents token reuse after password change
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Validate token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                # Save new password
                form.save(user)
                
                # Log password change
                ip_address = get_client_ip(request)
                PasswordChangeHistory.objects.create(
                    user=user,
                    ip_address=ip_address
                )
                
                # Log password reset confirmation
                log_audit_event(
                    request,
                    'PASSWORD_RESET_CONFIRM',
                    user=user,
                    affected_user=user,
                    severity='HIGH',
                    description=f'User {user.username} successfully reset their password via email link',
                    details={'username': user.username}
                )
                
                messages.success(
                    request,
                    'Your password has been reset successfully. '
                    'You can now login with your new password.'
                )
                return redirect('antoine:password_reset_complete')
        else:
            form = PasswordResetForm()
        
        return render(
            request,
            'antoine/password_reset_confirm.html',
            {'form': form, 'validlink': True}
        )
    else:
        # Invalid token (expired, modified, or wrong user)
        # Log invalid reset attempt for security monitoring
        try:
            # Try to extract user info if possible
            uid = force_str(urlsafe_base64_decode(uidb64))
            attempted_user = User.objects.get(pk=uid)
            username = attempted_user.username
            user_obj = attempted_user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            username = 'unknown'
            user_obj = None
        
        log_audit_event(
            request,
            'PASSWORD_RESET_REQUEST',
            user=user_obj,
            affected_user=user_obj,
            severity='MEDIUM',
            description=f'Invalid or expired password reset token attempted for user {username}',
            details={'username': username, 'reason': 'invalid_or_expired_token'}
        )
        
        messages.error(
            request,
            'The password reset link is invalid or has expired. '
            'Please request a new one.'
        )
        return render(
            request,
            'antoine/password_reset_confirm.html',
            {'validlink': False}
        )


def password_reset_complete(request):
    """
    Password reset complete view.
    Shows success message and link to login.
    """
    return render(request, 'antoine/password_reset_complete.html')


