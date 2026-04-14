from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .decorators import instructor_required

from .forms import RegistrationForm, LoginForm, UserPasswordChangeForm


def register(request):
    
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('eduard:dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'eduard/register.html', {'form': form})


def user_login(request):
    
    if request.user.is_authenticated:
        return redirect('eduard:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or request.GET.get('next')
            return redirect(next_url if next_url else 'eduard:dashboard')
    else:
        form = LoginForm(request)

    return render(request, 'eduard/login.html', {'form': form})


def user_logout(request):
    
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
    return redirect('eduard:login')


@login_required
def dashboard(request):
    
    return render(request, 'eduard/dashboard.html')


@login_required
def profile(request):
    
    return render(request, 'eduard/profile.html')


@login_required
def change_password(request):
    
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was updated successfully.')
            return redirect('eduard:profile')
    else:
        form = UserPasswordChangeForm(request.user)

    return render(request, 'eduard/change_password.html', {'form': form})


@instructor_required
def instructor_dashboard(request):
    """
    Accessible only to users in the Instructor group or staff/superusers.
    Normal authenticated users get a 403 Forbidden response.
    """
    from django.contrib.auth.models import User
    users = User.objects.all().order_by('date_joined')
    return render(request, 'eduard/instructor_dashboard.html', {'users': users})


def forbidden(request, exception=None):
    """
    Custom 403 handler — renders a friendly error page.
    """
    return render(request, 'eduard/403.html', status=403)