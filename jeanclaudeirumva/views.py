from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm, LoginForm, PasswordChangeForm, ProfileUpdateForm
from .models import UserProfile


def register_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Account created successfully! Welcome!")
            return redirect('jeanclaudeirumva:dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegistrationForm()
    return render(request, 'jeanclaudeirumva/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('jeanclaudeirumva:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'jeanclaudeirumva/login.html', {'form': form})


@login_required(login_url='jeanclaudeirumva:login')
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('jeanclaudeirumva:login')
    return render(request, 'jeanclaudeirumva/logout_confirm.html')


@login_required(login_url='jeanclaudeirumva:login')
def dashboard_view(request):
    return render(request, 'jeanclaudeirumva/dashboard.html', {'user': request.user})


@login_required(login_url='jeanclaudeirumva:login')
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('jeanclaudeirumva:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'jeanclaudeirumva/profile.html', {
        'user': request.user,
        'profile': profile,
        'form': form,
    })


@login_required(login_url='jeanclaudeirumva:login')
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            if not user.check_password(old_password):
                messages.error(request, "Old password is incorrect.")
            else:
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('jeanclaudeirumva:dashboard')
    else:
        form = PasswordChangeForm()
    return render(request, 'jeanclaudeirumva/password_change.html', {'form': form})