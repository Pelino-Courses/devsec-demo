from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegistrationForm, LoginForm, ProfileForm
from .models import Profile
import logging
audit_logger = logging.getLogger('asher_ndizeye.audit')

def log_security_event(event_type, username, status="SUCCESS", details=""):
    """
    Standardized logging for security events. 
    Never pass raw passwords or sensitive tokens here! [cite: 52, 62]
    """
    message = f"EVENT: {event_type} | USER: {username} | STATUS: {status} | DETAILS: {details}"
    if status == "FAILURE":
        audit_logger.warning(message)
    else:
        audit_logger.info(message)

def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            messages.success(request, "Account created! Please log in.")
            return redirect('login')
        # If form is NOT valid, it skips the IF and goes to the bottom render
    else:
        form = RegistrationForm()
    
    # CRITICAL: This must be outside the 'if request.method == 'POST'' block
    return render(request, 'asher_ndizeye/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Capture the 'next' parameter from the URL (GET) or the form (POST)
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            
            # --- SECURITY FIX: Validate the redirect target ---
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'asher_ndizeye/login.html', {'form': form, 'next': next_url})

@login_required
def user_logout(request):
    next_url = request.GET.get('next')
    logout(request)
    messages.info(request, "You have been logged out.")
    
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
        
    return redirect('login')

@login_required
def dashboard(request):
    return render(request, 'asher_ndizeye/dashboard.html')

@login_required
def profile(request):
    profile_instance, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile_instance, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile_instance, user=request.user)
    return render(request, 'asher_ndizeye/profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully!")
            return redirect('dashboard')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'asher_ndizeye/change_password.html', {'form': form})