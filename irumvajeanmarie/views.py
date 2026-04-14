from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, CustomPasswordChangeForm
from .models import Profile


def register_view(request):
    if request.user.is_authenticated:
        return redirect('irumvajeanmarie:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('irumvajeanmarie:login')
    else:
        form = RegisterForm()
    return render(request, 'irumvajeanmarie/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('irumvajeanmarie:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('irumvajeanmarie:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'irumvajeanmarie/login.html', {'form': form})


@login_required(login_url='irumvajeanmarie:login')
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('irumvajeanmarie:login')


@login_required(login_url='irumvajeanmarie:login')
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'irumvajeanmarie/dashboard.html', {'profile': profile})


@login_required(login_url='irumvajeanmarie:login')
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('irumvajeanmarie:profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'irumvajeanmarie/profile.html', {'form': form, 'profile': profile})


@login_required(login_url='irumvajeanmarie:login')
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('irumvajeanmarie:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'irumvajeanmarie/password_change.html', {'form': form})