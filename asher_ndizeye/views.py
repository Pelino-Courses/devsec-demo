from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .forms import RegistrationForm, LoginForm, ProfileForm
from .models import Profile


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
    else:
        form = RegistrationForm()
    return render(request, 'asher_ndizeye/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            print("✅ LOGIN SUCCESS")
            login(request, form.get_user())
            return redirect('dashboard')
        else:
            print("❌ LOGIN FAILED")
            print(form.errors)

    else:
        form = LoginForm()

    return render(request, 'asher_ndizeye/login.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
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