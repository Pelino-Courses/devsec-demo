from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .models import UserProfile

def get_safe_redirect_url(request, redirect_to, fallback_url):
    """
    Validate the redirect URL to prevent open redirect vulnerabilities.
    
    Security logic:
    - Uses url_has_allowed_host_and_scheme to ensure the URL is safe for the 
      current domain and protocol.
    - Rejects external/malicious URLs by falling back to a safe internal URL.
    """
    if redirect_to and url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return fallback_url

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    redirect_to = request.POST.get('next') or request.GET.get('next')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            messages.success(request, 'Registration successful. Please login.')
            
            # Use safe redirect helper for post-registration navigation
            safe_url = get_safe_redirect_url(request, redirect_to, 'login')
            return redirect(safe_url)
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form, 'next': redirect_to})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
        
    redirect_to = request.POST.get('next') or request.GET.get('next')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # FIXED: Validate 'next' parameter to prevent open redirects
            safe_url = get_safe_redirect_url(request, redirect_to, 'profile')
            return redirect(safe_url)
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form, 'next': redirect_to})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')
