from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm, CustomPasswordChangeForm


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('ndayishimiye:profile')
    else:
        form = RegisterForm()
    return render(request, 'ndayishimiye/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Logged in successfully!')
            return redirect('ndayishimiye:profile')
    else:
        form = LoginForm()
    return render(request, 'ndayishimiye/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('ndayishimiye:login')


@login_required
def profile(request):
    return render(request, 'ndayishimiye/profile.html')


@login_required
def password_change(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('ndayishimiye:profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'ndayishimiye/password_change.html', {'form': form})
    