from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden
from django.forms import ValidationError
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme
import logging
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, UserPasswordChangeForm, UserProfileUploadForm
from .models import UserProfile
from .permissions import user_is_staff, user_is_instructor, check_user_role, user_owns_object

# Get security logger
security_logger = logging.getLogger('security_audit')

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes in seconds


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration."""
    # Get redirect target
    next_url = request.GET.get('next', 'mucyo_aime_maxime:profile')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            security_logger.info(f"USER_REGISTRATION_SUCCESS: User '{user.username}' (ID: {user.id}) registered from IP {request.META.get('REMOTE_ADDR')}")
            messages.success(
                request,
                f'Account created successfully! Welcome, {user.username}.'
            )
            login(request, user)

            # Validate next_url to prevent open redirects
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('mucyo_aime_maxime:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'mucyo_aime_maxime/register.html', {'form': form, 'next': next_url})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
    # Get redirect target
    next_url = request.GET.get('next', 'mucyo_aime_maxime:profile')

    if request.user.is_authenticated:
        return redirect('mucyo_aime_maxime:profile')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Check for existing lockout
            lockout_key = f"lockout_{username}"
            if cache.get(lockout_key):
                security_logger.warning(f"LOGIN_LOCKOUT_ENFORCED: Account '{username}' from IP {request.META.get('REMOTE_ADDR')}")
                messages.error(
                    request,
                    'Too many failed attempts. Please try again in 5 minutes.'
                )
                return render(request, 'mucyo_aime_maxime/login.html', {'form': form, 'next': next_url})
            
            user = authenticate(request, username=username, password=password)
            attempts_key = f"login_attempts_{username}"
            
            if user is not None:
                # Clear attempts on successful login
                cache.delete(attempts_key)
                
                login(request, user)
                security_logger.info(f"LOGIN_SUCCESS: User '{user.username}' (ID: {user.id}) logged in from IP {request.META.get('REMOTE_ADDR')}")
                messages.success(request, f'Welcome back, {user.username}!')

                # Validate next_url to prevent open redirects
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure()
                ):
                    return redirect(next_url)
                return redirect('mucyo_aime_maxime:profile')
            else:
                # Increment failed attempts
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=LOCKOUT_DURATION)
                
                if attempts >= MAX_LOGIN_ATTEMPTS:
                    cache.set(lockout_key, True, timeout=LOCKOUT_DURATION)
                    security_logger.warning(f"LOGIN_LOCKOUT_TRIGGERED: Account '{username}' reached max attempts from IP {request.META.get('REMOTE_ADDR')}")
                    messages.error(
                        request,
                        'Too many failed attempts. Please try again in 5 minutes.'
                    )
                else:
                    security_logger.info(f"LOGIN_FAILURE: Invalid attempt for account '{username}' (Attempt {attempts}/{MAX_LOGIN_ATTEMPTS}) from IP {request.META.get('REMOTE_ADDR')}")
                    messages.error(
                        request,
                        'Invalid username or password. Please try again.'
                    )
    else:
        form = UserLoginForm()
    
    return render(request, 'mucyo_aime_maxime/login.html', {'form': form, 'next': next_url})


@require_http_methods(["POST"])
@login_required(login_url='mucyo_aime_maxime:login')
def logout_view(request):
    """Handle user logout."""
    # Get redirect target
    next_url = request.POST.get('next', 'mucyo_aime_maxime:login')

    username = request.user.username
    user_id = request.user.id
    logout(request)
    security_logger.info(f"LOGOUT: User '{username}' (ID: {user_id}) logged out.")
    messages.success(request, 'You have been logged out successfully.')

    # Validate next_url to prevent open redirects
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        if next_url.startswith('/'):
            return redirect(next_url)
        return redirect(next_url)
    return redirect('mucyo_aime_maxime:login')


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    Display and handle user profile updates for the current user.
    """
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=user)
        upload_form = UserProfileUploadForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and upload_form.is_valid():
            user_form.save()
            upload_form.save()
            security_logger.info(f"PROFILE_UPDATE: User '{user.username}' (ID: {user.id}) updated their profile and/or uploads.")
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('mucyo_aime_maxime:profile')
    else:
        user_form = UserProfileForm(instance=user)
        upload_form = UserProfileUploadForm(instance=profile)
    
    return render(request, 'mucyo_aime_maxime/profile.html', {
        'form': user_form,
        'upload_form': upload_form,
        'profile': profile
    })


@login_required(login_url='mucyo_aime_maxime:login')
@user_owns_object
@require_http_methods(["GET", "POST"])
def profile_detail_view(request, user_id=None):
    """
    Display and handle user profile updates by user ID (with IDOR prevention).
    """
    try:
        target_user = User.objects.get(id=user_id)
        target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('mucyo_aime_maxime:profile')
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=target_user)
        upload_form = UserProfileUploadForm(request.POST, request.FILES, instance=target_profile)

        if user_form.is_valid() and upload_form.is_valid():
            user_form.save()
            upload_form.save()
            security_logger.info(f"PROFILE_DETAIL_UPDATE: User '{request.user.username}' (ID: {request.user.id}) updated profile of '{target_user.username}' (ID: {target_user.id}).")
            messages.success(request, 'Profile has been updated successfully.')
            return redirect('mucyo_aime_maxime:profile_detail', user_id=user_id)
    else:
        user_form = UserProfileForm(instance=target_user)
        upload_form = UserProfileUploadForm(instance=target_profile)
    
    context = {
        'form': user_form,
        'upload_form': upload_form,
        'target_user': target_user,
        'profile': target_profile,
        'is_own_profile': request.user.id == target_user.id,
    }
    return render(request, 'mucyo_aime_maxime/profile.html', context)


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    """
    Handle user password change.
    
    Object-level access control: Users can only change their own password.
    This prevents IDOR vulnerabilities by ensuring password changes are restricted
    to the authenticated user only.
    """
    # Explicit access control check: ensure user can only change their own password
    user = request.user
    
    if request.method == 'POST':
        form = UserPasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            security_logger.info(f"PASSWORD_CHANGE_SUCCESS: User '{user.username}' (ID: {user.id}) changed their password.")
            messages.success(
                request,
                'Your password has been changed successfully.'
            )
            return redirect('mucyo_aime_maxime:profile')
        else:
            security_logger.warning(f"PASSWORD_CHANGE_FAILURE: User '{user.username}' (ID: {user.id}) failed to change password.")
    else:
        form = UserPasswordChangeForm(user)
    
    return render(request, 'mucyo_aime_maxime/password_change.html', {'form': form})


@user_is_staff
@require_http_methods(["GET"])
def staff_dashboard_view(request):
    """
    Staff-only dashboard for managing users and permissions.
    
    Accessible only by users in the 'Staff' group or superusers.
    Displays all users and their roles.
    """
    all_users = User.objects.all()
    user_roles = {}
    
    for user in all_users:
        user_roles[user.id] = check_user_role(user)
    
    context = {
        'all_users': all_users,
        'user_roles': user_roles,
    }
    return render(request, 'mucyo_aime_maxime/staff_dashboard.html', context)


@user_is_instructor
@require_http_methods(["GET"])
def instructor_reports_view(request):
    """
    Instructor-only view for accessing user activity and reports.
    
    Accessible only by users in the 'Instructor' group or superusers.
    Displays user registration statistics and activity summaries.
    """
    total_users = User.objects.count()
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    context = {
        'total_users': total_users,
        'recent_users': recent_users,
    }
    return render(request, 'mucyo_aime_maxime/instructor_reports.html', context)

