from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.exceptions import PermissionDenied  # Required for IDOR protection
from .forms import RegistrationForm, LoginForm, ProfileForm
from .models import Profile
import logging

audit_logger = logging.getLogger('asher_ndizeye.audit')

def log_security_event(event_type, username, status="SUCCESS", details=""):
    message = f"EVENT: {event_type} | USER: {username} | STATUS: {status} | DETAILS: {details}"
    if status == "FAILURE":
        audit_logger.warning(message)
    else:
        audit_logger.info(message)

# --- ROLE-BASED ACCESS CONTROL VIEW ---
class StaffDashboardView(UserPassesTestMixin, ListView):
    model = User
    template_name = 'asher_ndizeye/staff_dashboard.html'
    context_object_name = 'users'

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        log_security_event("UNAUTHORIZED_ACCESS", self.request.user.username, "FAILURE", "Attempted to access Staff Dashboard")
        messages.error(self.request, "Access Denied: Staff permissions required.")
        return redirect('asher_ndizeye:dashboard')

def register(request):
    if request.user.is_authenticated:
        return redirect('asher_ndizeye:dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            log_security_event("REGISTRATION", user.username, "SUCCESS")
            messages.success(request, "Account created! Please log in.")
            return redirect('asher_ndizeye:login')
        else:
            log_security_event("REGISTRATION", request.POST.get('username', 'unknown'), "FAILURE", "Invalid form data")
    else:
        form = RegistrationForm()
    return render(request, 'asher_ndizeye/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('asher_ndizeye:dashboard')

    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            log_security_event("LOGIN", user.username, "SUCCESS")
            
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('asher_ndizeye:dashboard')
        else:
            log_security_event("LOGIN", request.POST.get('username', 'unknown'), "FAILURE")
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'asher_ndizeye/login.html', {'form': form, 'next': next_url})

@login_required
def user_logout(request):
    username = request.user.username
    logout(request)
    log_security_event("LOGOUT", username, "SUCCESS")
    messages.info(request, "You have been logged out.")
    return redirect('asher_ndizeye:login')

@login_required
def dashboard(request):
    return render(request, 'asher_ndizeye/dashboard.html')

@login_required
def profile(request):
    """
    PREVENT IDOR: 
    We do not accept a 'user_id' in the URL. We fetch the profile 
    directly using request.user to ensure users only access their own data.
    """
    # Force lookup by the authenticated session user
    profile_instance, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile_instance, user=request.user)
        if form.is_valid():
            # Explicit Object-Level Access Check:
            # Ensure the instance being saved actually belongs to the user in the request
            if profile_instance.user != request.user:
                log_security_event("IDOR_ATTEMPT", request.user.username, "FAILURE", "User tried to modify another profile")
                raise PermissionDenied("You do not have permission to edit this profile.")

            form.save()
            log_security_event("PROFILE_UPDATE", request.user.username, "SUCCESS")
            messages.success(request, "Profile updated successfully!")
            return redirect('asher_ndizeye:profile')
        else:
            log_security_event("PROFILE_UPDATE", request.user.username, "FAILURE", "Invalid profile data submission")
    else:
        form = ProfileForm(instance=profile_instance, user=request.user)
        
    return render(request, 'asher_ndizeye/profile.html', {
        'form': form,
        'profile_instance': profile_instance
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            log_security_event("PASSWORD_CHANGE", user.username, "SUCCESS")
            messages.success(request, "Password changed successfully!")
            return redirect('asher_ndizeye:dashboard')
        else:
            log_security_event("PASSWORD_CHANGE", request.user.username, "FAILURE")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'asher_ndizeye/change_password.html', {'form': form})