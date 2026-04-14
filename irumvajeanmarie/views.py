from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
from datetime import timedelta
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, CustomPasswordChangeForm
from .models import Profile, LoginAttempt, AccountLockout, ContactMessage
from .decorators import instructor_required, admin_required


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def register_view(request):
    if request.user.is_authenticated:
        return redirect('irumvajeanmarie:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user, role=Profile.ROLE_STUDENT)
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('irumvajeanmarie:login')
    else:
        form = RegisterForm()
    return render(request, 'irumvajeanmarie/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('irumvajeanmarie:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        ip_address = get_client_ip(request)

        if username:
            try:
                lockout = AccountLockout.objects.get(username=username)
                if lockout.locked_until > timezone.now():
                    messages.error(request, 'Account is locked due to too many failed login attempts. Please try again later.')
                    form = LoginForm(request, data=request.POST)
                    return render(request, 'irumvajeanmarie/login.html', {'form': form})
                else:
                    lockout.delete()
            except AccountLockout.DoesNotExist:
                pass

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if username:
                LoginAttempt.objects.create(username=username, ip_address=ip_address, was_successful=True)
                AccountLockout.objects.filter(username=username).delete()
                LoginAttempt.objects.filter(username=username, was_successful=False).delete()

            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('irumvajeanmarie:dashboard')
        else:
            if username:
                LoginAttempt.objects.create(username=username, ip_address=ip_address, was_successful=False)
                recent_failures = LoginAttempt.objects.filter(
                    username=username,
                    was_successful=False,
                    timestamp__gte=timezone.now() - timedelta(minutes=15)
                ).count()

                if recent_failures >= 5:
                    AccountLockout.objects.update_or_create(
                        username=username,
                        defaults={'locked_until': timezone.now() + timedelta(minutes=15)}
                    )
                    messages.error(request, 'Account is locked due to too many failed login attempts. Please try again later.')
                else:
                    messages.error(request, 'Invalid username or password.')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'irumvajeanmarie/login.html', {'form': form})


@login_required(login_url='irumvajeanmarie:login')
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('irumvajeanmarie:login')


@login_required(login_url='irumvajeanmarie:login')
def dashboard_view(request):
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': Profile.ROLE_STUDENT}
    )
    return render(request, 'irumvajeanmarie/dashboard.html', {'profile': profile})


@login_required(login_url='irumvajeanmarie:login')
def profile_view(request):
    # IDOR FIX: always load the profile of the currently authenticated user
    # Never accept a user ID or profile ID from the URL
    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={'role': Profile.ROLE_STUDENT}
    )
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('irumvajeanmarie:profile')
    else:
        form = ProfileUpdateForm(instance=profile)
    return render(request, 'irumvajeanmarie/profile.html', {'form': form, 'profile': profile})


@login_required(login_url='irumvajeanmarie:login')
def view_profile(request, username):
    # IDOR FIX: only the owner can view their own profile
    # Instructors and admins may view any profile
    profile = get_object_or_404(Profile, user__username=username)
    requester_profile = get_object_or_404(Profile, user=request.user)

    is_owner = profile.user == request.user
    is_privileged = requester_profile.role in [
        Profile.ROLE_INSTRUCTOR, Profile.ROLE_ADMIN
    ]

    if not is_owner and not is_privileged:
        return HttpResponseForbidden(
            "Access denied: You are not allowed to view this profile."
        )

    return render(request, 'irumvajeanmarie/view_profile.html', {
        'profile': profile,
        'is_owner': is_owner,
    })


@login_required(login_url='irumvajeanmarie:login')
def password_change_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('irumvajeanmarie:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'irumvajeanmarie/password_change.html', {'form': form})


# ─── INSTRUCTOR ONLY VIEW ─────────────────────────────────────

@login_required(login_url='irumvajeanmarie:login')
@instructor_required
def instructor_panel(request):
    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT).select_related('user')
    return render(request, 'irumvajeanmarie/instructor_panel.html', {
        'students': students
    })


# ─── ADMIN ONLY VIEW ──────────────────────────────────────────

@login_required(login_url='irumvajeanmarie:login')
@admin_required
def admin_panel(request):
    all_profiles = Profile.objects.all().select_related('user')
    return render(request, 'irumvajeanmarie/admin_panel.html', {
        'profiles': all_profiles
    })


@login_required(login_url='irumvajeanmarie:login')
def contact_page_view(request):
    return render(request, 'irumvajeanmarie/contact.html')


@login_required(login_url='irumvajeanmarie:login')
@require_POST
def contact_view(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
    except Exception:
        message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'status': 'error', 'message': 'Message is empty'}, status=400)
        
    ContactMessage.objects.create(user=request.user, message=message)
    return JsonResponse({'status': 'success', 'message': 'Message sent successfully.'})