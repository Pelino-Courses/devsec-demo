from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from .decorators import instructor_required
from .forms import RegistrationForm, LoginForm, ProfileUpdateForm


def register(request):
    if request.user.is_authenticated:
        return redirect('tresor:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('tresor:dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'tresor/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('tresor:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}.')
            next_url = request.GET.get('next', 'tresor:dashboard')
            return redirect(next_url)
    else:
        form = LoginForm()
    return render(request, 'tresor/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('tresor:login')
    return render(request, 'tresor/logout_confirm.html')


@login_required
def dashboard(request):
    is_instructor = (
        request.user.groups.filter(name='instructor').exists()
        or request.user.is_staff
    )
    return render(request, 'tresor/dashboard.html', {'is_instructor': is_instructor})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('tresor:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'tresor/profile.html', {'form': form})


@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('tresor:password_change_done')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'tresor/password_change.html', {'form': form})


@login_required
def password_change_done(request):
    return render(request, 'tresor/password_change_done.html')


@instructor_required
def instructor_dashboard(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'tresor/instructor_dashboard.html', {'users': users})
