from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.http import Http404
from django.contrib.auth.models import User
from .models import Profile
import logging

logger = logging.getLogger('security')

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
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
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
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'shema/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')

@login_required
def profile_view(request, username):
    # Object-level authorization check: Prevent Insecure Direct Object Reference (IDOR)
    # Ensure the user accessing the profile is actually the owner of the profile.
    if request.user.username != username:
        # Avoid leaking existence information by returning a 404 rather than a 403 Forbidden
        raise Http404("Profile not found")
        
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'shema/profile.html', {'profile_user': profile_user})

@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'shema/password_change.html', {'form': form})

@login_required
@permission_required('shema.view_instructor_dashboard', raise_exception=True)
def instructor_dashboard_view(request):
    return render(request, 'shema/instructor_dashboard.html')

@login_required
def update_profile_view(request, username):
    # Object-level authorization check: Prevent IDOR modification
    # Ensure ONLY the owner can update their profile.
    if request.user.username != username:
        raise Http404("Profile not found")
        
    profile_user = get_object_or_404(User, username=username)
    
    if request.method == 'POST':
        bio = request.POST.get('bio', '')
        profile_user.profile.bio = bio
        profile_user.profile.save()
        messages.success(request, "Profile details updated successfully!")
        return redirect('profile', username=username)
    
    return redirect('profile', username=username)
