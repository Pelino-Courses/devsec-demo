from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile
from .decorators import admin_required, editor_required


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, role='viewer')
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
        messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out.')
    return redirect('login')


@login_required
def home(request):
    profile = UserProfile.objects.get(user=request.user)
    return render(request, 'accounts/dashboard.html', {'profile': profile})


@admin_required
def admin_dashboard(request):
    """Admin-only dashboard showing all users."""
    all_users = UserProfile.objects.all()
    return render(request, 'accounts/admin_dashboard.html', {'users': all_users})


@editor_required
def editor_panel(request):
    """Editor panel for users with editor or admin role."""
    profile = UserProfile.objects.get(user=request.user)
    return render(request, 'accounts/editor_panel.html', {'profile': profile})


@login_required
def profile_view(request):
    """View current user's profile."""
    profile = UserProfile.objects.get(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})