import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import Http404
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegisterForm, LoginForm, CustomPasswordChangeForm
from .forms import ProfileBioForm
from .models import UserProfile

audit_log = logging.getLogger('ndayishimiye.audit')
DJANGO_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _get_safe_redirect(request, fallback):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            login(request, user, backend=DJANGO_BACKEND)
            audit_log.info(
                'REGISTER_SUCCESS username=%s ip=%s',
                user.username,
                request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Account created successfully!')
            return redirect(_get_safe_redirect(
                request, 'ndayishimiye:profile'
            ))
        else:
            audit_log.warning(
                'REGISTER_FAILURE ip=%s',
                request.META.get('REMOTE_ADDR'),
            )
    else:
        form = RegisterForm()
    return render(request, 'ndayishimiye/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend=DJANGO_BACKEND)
            audit_log.info(
                'LOGIN_SUCCESS username=%s ip=%s',
                user.username,
                request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Logged in successfully!')
            return redirect(_get_safe_redirect(
                request, 'ndayishimiye:profile'
            ))
        else:
            audit_log.warning(
                'LOGIN_FAILURE username=%s ip=%s',
                request.POST.get('username', ''),
                request.META.get('REMOTE_ADDR'),
            )
    else:
        form = LoginForm()
    return render(request, 'ndayishimiye/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
    else:
        username = 'anonymous'
    audit_log.info(
        'LOGOUT username=%s ip=%s',
        username,
        request.META.get('REMOTE_ADDR'),
    )
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('ndayishimiye:login')


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileBioForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            audit_log.info(
                'PROFILE_BIO_UPDATE username=%s ip=%s',
                request.user.username,
                request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Bio updated successfully!')
            return redirect('ndayishimiye:profile')
    else:
        form = ProfileBioForm(instance=profile_obj)
    return render(request, 'ndayishimiye/profile.html', {
        'form': form,
        'profile': profile_obj,
    })


@login_required
def profile_by_id(request, user_id):
    if request.user.id != user_id and not request.user.is_staff:
        raise Http404
    user = get_object_or_404(User, id=user_id)
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)
    return render(request, 'ndayishimiye/profile.html', {
        'viewed_user': user,
        'profile': profile_obj,
    })


@login_required
def password_change(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            audit_log.info(
                'PASSWORD_CHANGE_SUCCESS username=%s ip=%s',
                request.user.username,
                request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, 'Password changed successfully!')
            return redirect('ndayishimiye:profile')
        else:
            audit_log.warning(
                'PASSWORD_CHANGE_FAILURE username=%s ip=%s',
                request.user.username,
                request.META.get('REMOTE_ADDR'),
            )
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
        audit_log.info(
            'PROFILE_UPDATE username=%s ip=%s',
            request.user.username,
            request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, 'Email updated successfully!')
    return redirect('ndayishimiye:profile')
