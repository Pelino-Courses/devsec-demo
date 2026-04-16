from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
import logging

logger = logging.getLogger('security')

def get_safe_redirect(request, default='home'):
    """
    Safely extracts and validates a redirect target from GET or POST.
    """
    redirect_to = request.POST.get('next', request.GET.get('next', ''))
    
    if not url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return default
    return redirect_to or default

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
            return redirect(get_safe_redirect(request))
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
                return redirect(get_safe_redirect(request))
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'shema/login.html', {'form': form})

def logout_view(request):
    target = get_safe_redirect(request)
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect(target)

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
            return redirect(get_safe_redirect(request, default='profile'))
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'shema/password_change.html', {'form': form})

@login_required
@permission_required('shema.view_instructor_dashboard', raise_exception=True)
def instructor_dashboard_view(request):
    return render(request, 'shema/instructor_dashboard.html')
