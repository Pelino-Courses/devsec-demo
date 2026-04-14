from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .forms import RegistrationForm, LoginForm, PasswordChangeForm


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
    """
    Own profile view - always shows the current user's profile.
    No user_id parameter accepted here to prevent IDOR.
    """
    return render(request, 'jeanclaudeirumva/profile.html', {'user': request.user})


@login_required(login_url='jeanclaudeirumva:login')
def profile_detail_view(request, user_id):
    """
    View another user's profile by ID.
    IDOR protection: only allow access to own profile.
    Attempting to access another user's profile returns 404.
    """
    if request.user.id != user_id:
        raise Http404("Profile not found.")
    user = get_object_or_404(User, id=user_id)
    return render(request, 'jeanclaudeirumva/profile.html', {'user': user})


@login_required(login_url='jeanclaudeirumva:login')
def password_change_view(request):
    """
    Password change view - always operates on the current user.
    No user_id parameter accepted to prevent IDOR.
    """
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