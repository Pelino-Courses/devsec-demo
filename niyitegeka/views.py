from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import (
    RegisterForm,
    LoginForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)
from .models import Profile
from .decorators import staff_required


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            messages.success(
                request,
                'Account created successfully. Please log in.'
            )
            return redirect('niyitegeka:login')
    else:
        form = RegisterForm()
    return render(request, 'niyitegeka/register.html', {'form': form})


def loginview(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('niyitegeka:dashboard')
    else:
        form = LoginForm()
    return render(request, 'niyitegeka/login.html', {'form': form})


def logoutview(request):
    logout(request)
    return redirect('niyitegeka:login')


@login_required
def dashboard(request):
    return render(request, 'niyitegeka/dashboard.html')


@login_required
def profile(request):
    userprofile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('niyitegeka:profile')
    else:
        form = ProfileUpdateForm(instance=userprofile)
    return render(request, 'niyitegeka/profile.html', {'form': form})


@login_required
def passwordchange(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('niyitegeka:dashboard')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(
        request,
        'niyitegeka/password_change.html',
        {'form': form}
    )


@staff_required
def staffdashboard(request):
    users = User.objects.all().order_by('username')
    return render(
        request,
        'niyitegeka/staff_dashboard.html',
        {'users': users}
    )
