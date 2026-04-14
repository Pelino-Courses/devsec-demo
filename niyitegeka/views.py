from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from .forms import (
    RegisterForm,
    LoginForm,
    ProfileUpdateForm,
    CustomPasswordChangeForm,
)
from .models import Profile, LoginAttempt
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
        username = request.POST.get('username', '')
        attempt, created = LoginAttempt.objects.get_or_create(
            username=username
        )
        if attempt.is_locked():
            messages.error(
                request,
                'Account temporarily locked due to too many failed attempts. '
                'Please try again in 10 minutes.'
            )
            return render(
                request,
                'niyitegeka/login.html',
                {'form': form}
            )
        if form.is_valid():
            user = form.get_user()
            attempt.reset()
            login(request, user)
            return redirect('niyitegeka:dashboard')
        else:
            attempt.increment()
            remaining = 5 - attempt.attempts
            if remaining > 0:
                messages.error(
                    request,
                    f'Invalid credentials. {remaining} attempts remaining '
                    f'before account is locked.'
                )
            else:
                messages.error(
                    request,
                    'Account locked for 10 minutes due to too many '
                    'failed attempts.'
                )
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


@login_required
def profiledetail(request, username):
    if request.user.username != username and not request.user.is_staff:
        raise PermissionDenied
    targetuser = get_object_or_404(User, username=username)
    userprofile = get_object_or_404(Profile, user=targetuser)
    return render(
        request,
        'niyitegeka/profile_detail.html',
        {'targetuser': targetuser, 'userprofile': userprofile}
    )


@login_required
def updatebio(request):
    if request.method == 'POST':
        bio = request.POST.get('bio', '')
        userprofile, created = Profile.objects.get_or_create(
            user=request.user
        )
        userprofile.bio = bio
        userprofile.save()
        return JsonResponse({'status': 'ok', 'bio': bio})
    return JsonResponse({'status': 'error'}, status=400)
