from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm, LoginForm, PasswordChangeForm
from .security import (
    is_account_locked,
    register_failed_attempt,
    reset_failed_attempts,
    get_remaining_attempts,
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
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
        username = request.POST.get('username', '')

        if is_account_locked(username):
            messages.error(
                request,
                "Your account is temporarily locked due to too many failed "
                "login attempts. Please try again in 15 minutes."
            )
            return render(request, 'jeanclaudeirumva/login.html', {'form': form})

        if form.is_valid():
            user = form.get_user()
            reset_failed_attempts(username)
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('jeanclaudeirumva:dashboard')
        else:
            register_failed_attempt(username)
            remaining = get_remaining_attempts(username)
            if remaining == 0:
                messages.error(
                    request,
                    "Your account has been locked for 15 minutes due to too "
                    "many failed attempts."
                )
            else:
                messages.error(
                    request,
                    f"Invalid username or password. "
                    f"{remaining} attempt(s) remaining before lockout."
                )
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
    return render(request, 'jeanclaudeirumva/profile.html', {'user': request.user})


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