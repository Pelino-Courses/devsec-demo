from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden
from django.forms import ValidationError
from django.core.cache import cache
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, UserPasswordChangeForm
from .permissions import user_is_staff, user_is_instructor, check_user_role, user_owns_object

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes in seconds


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Account created successfully! Welcome, {user.username}.'
            )
            login(request, user)
            return redirect('mucyo_aime_maxime:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'mucyo_aime_maxime/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
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
                messages.error(
                    request,
                    'Too many failed attempts. Please try again in 5 minutes.'
                )
                return render(request, 'mucyo_aime_maxime/login.html', {'form': form})
            
            user = authenticate(request, username=username, password=password)
            attempts_key = f"login_attempts_{username}"
            
            if user is not None:
                # Clear attempts on successful login
                cache.delete(attempts_key)
                
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('mucyo_aime_maxime:profile')
            else:
                # Increment failed attempts
                attempts = cache.get(attempts_key, 0) + 1
                cache.set(attempts_key, attempts, timeout=LOCKOUT_DURATION)
                
                if attempts >= MAX_LOGIN_ATTEMPTS:
                    cache.set(lockout_key, True, timeout=LOCKOUT_DURATION)
                    messages.error(
                        request,
                        'Too many failed attempts. Please try again in 5 minutes.'
                    )
                else:
                    messages.error(
                        request,
                        'Invalid username or password. Please try again.'
                    )
    else:
        form = UserLoginForm()
    
    return render(request, 'mucyo_aime_maxime/login.html', {'form': form})


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["POST"])
def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('mucyo_aime_maxime:login')


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """
    Display and handle user profile updates for the current user.
    
    Object-level access control: Users can only view and modify their own profile.
    This prevents IDOR vulnerabilities by ensuring profile operations are restricted
    to the authenticated user only.
    """
    # Explicit access control check: ensure user can only access their own profile
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('mucyo_aime_maxime:profile')
    else:
        form = UserProfileForm(instance=user)
    
    return render(request, 'mucyo_aime_maxime/profile.html', {'form': form})


@login_required(login_url='mucyo_aime_maxime:login')
@user_owns_object
@require_http_methods(["GET", "POST"])
def profile_detail_view(request, user_id=None):
    """
    Display and handle user profile updates by user ID (with IDOR prevention).
    
    Object-level access control: Users can only view/modify their own profile.
    The @user_owns_object decorator ensures that:
    - The requested user exists
    - The requesting user is either the target user or a superuser
    - Unauthorized access returns 403 Forbidden
    
    This view demonstrates proper IDOR prevention when accepting user IDs as parameters.
    """
    # Get the target user (already verified by @user_owns_object decorator)
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('mucyo_aime_maxime:profile')
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile has been updated successfully.')
            return redirect('mucyo_aime_maxime:profile_detail', user_id=user_id)
    else:
        form = UserProfileForm(instance=target_user)
    
    context = {
        'form': form,
        'target_user': target_user,
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
            messages.success(
                request,
                'Your password has been changed successfully.'
            )
            return redirect('mucyo_aime_maxime:profile')
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

