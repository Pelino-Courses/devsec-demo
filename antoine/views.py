from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import IntegrityError
from django.http import HttpResponseForbidden

from .models import UserProfile, LoginHistory, PasswordChangeHistory
from .forms import (
    RegistrationForm, LoginForm, UserProfileForm,
    CustomPasswordChangeForm
)
from .permissions import (
    admin_required, instructor_required, has_permission,
    get_user_role, is_admin, is_instructor
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
    User login view with session creation.
    Logs login attempts to LoginHistory model.
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
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session timeout
                if remember_me:
                    request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
                else:
                    request.session.set_expiry(0)  # Browser close
                
                # Log successful login
                LoginHistory.objects.create(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True
                )
                
                # Update last login IP
                try:
                    profile = user.antoine_profile
                    profile.last_login_ip = ip_address
                    profile.save()
                except UserProfile.DoesNotExist:
                    UserProfile.objects.create(user=user, last_login_ip=ip_address)
                
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Redirect to next URL or dashboard
                next_url = request.GET.get('next', 'antoine:dashboard')
                if next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('antoine:dashboard')
            else:
                # Log failed login
                try:
                    user_obj = User.objects.get(username=username)
                except User.DoesNotExist:
                    user_obj = None
                
                if user_obj:
                    LoginHistory.objects.create(
                        user=user_obj,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=False,
                        failure_reason='Invalid password'
                    )
                
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    return render(request, 'antoine/login.html', {'form': form})


@login_required(login_url='antoine:login')
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    User logout view.
    Clears session and redirects to home page.
    """
    user = request.user
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
def profile_view(request):
    """
    User profile view and update.
    Allows users to update their profile information.
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
def change_password(request):
    """
    Change password view.
    Allows authenticated users to change their password.
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
    Only shows basic public information.
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
def reset_user_password(request, user_id):
    """
    Admin-only view to reset another user's password.
    Generates a temporary password and logs the action.
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


