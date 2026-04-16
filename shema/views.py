from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger('security')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def home(request):
    return render(request, 'shema/home.html')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ip = request.META.get('REMOTE_ADDR')
            logger.info(f"NEW_USER_REGISTERED: '{user.username}' from IP {ip}")
            messages.success(request, f"Account created successfully for {user.username}!")
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'shema/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        username = request.POST.get('username')
        ip = get_client_ip(request)
        attempts_key = f"login_attempts_{username}_{ip}"
        attempts_count = cache.get(attempts_key, 0)

        # 1. Pre-check: Threshold check (5 attempts)
        if attempts_count >= 5:
            logger.warning(f"BRUTE_FORCE_TRIGGERED: Blocked attempt for user '{username}' from IP {ip}")
            messages.error(request, "Too many failed login attempts. Please try again after 5 minutes.")
            return render(request, 'shema/login.html', {'form': form})

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Clear attempts on success
                cache.delete(attempts_key)
                
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")
                
                # Secure redirect handling
                next_url = request.GET.get('next', 'home')
                if not url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = 'home'
                return redirect(next_url)
        else:
            # Increment attempts on failure
            cache.set(attempts_key, attempts_count + 1, 300) # 300 seconds = 5 minutes
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'shema/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'shema/profile.html')

@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'shema/password_change.html', {'form': form})

@login_required
@permission_required('shema.view_instructor_dashboard', raise_exception=True)
def instructor_dashboard_view(request):
    return render(request, 'shema/instructor_dashboard.html')
