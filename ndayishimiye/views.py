from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import Http404
from django.views.decorators.http import require_POST
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
def profile_by_id(request, user_id):
    if request.user.id != user_id and not request.user.is_staff:
        raise Http404
    user = get_object_or_404(User, id=user_id)
    return render(request, 'ndayishimiye/profile.html', {'viewed_user': user})


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


def is_staff_user(user):
    return user.is_staff


def home(request):
    return render(request, 'ndayishimiye/home.html')


@login_required
@user_passes_test(is_staff_user)
def staff_dashboard(request):
    users = User.objects.all()
    context = {'users': users}
    return render(request, 'ndayishimiye/staff_dashboard.html', context)


@login_required
@require_POST
def profile_update(request):
    new_email = request.POST.get('email', '')
    if new_email:
        request.user.email = new_email
        request.user.save()
        messages.success(request, 'Email updated successfully!')
    return redirect('ndayishimiye:profile')
