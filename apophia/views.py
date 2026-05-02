from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta

from .models import LoginAttempt
from .forms import ApophiaUserCreationForm, UserUpdateForm, ProfileUpdateForm

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = ApophiaUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
    else:
        form = ApophiaUserCreationForm()
    return render(request, 'apophia/register.html', {'form': form})

@login_required
def profile(request, username=None):
    # Determine target user: either current user or one specified in URL
    if username:
        target_user = get_object_or_404(User, username=username)
    else:
        target_user = request.user

    # RBAC/IDOR Check: Only self or staff can access
    if target_user != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to access another user's profile.")

    if request.method == 'POST':
        # Safety Check: Even staff cannot modify another's credentials/details here
        if target_user != request.user:
            raise PermissionDenied("You cannot modify another user's profile information.")

        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=target_user)
        p_form = ProfileUpdateForm(instance=target_user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'target_user': target_user
    }
    return render(request, 'apophia/profile.html', context)

class ApophiaLoginView(LoginView):
    template_name = 'apophia/login.html'
    redirect_authenticated_user = True

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        ip_address = self.get_client_ip()
        
        # Check for lockout (5 failures in the last 15 minutes)
        fifteen_mins_ago = timezone.now() - timedelta(minutes=15)
        failures = LoginAttempt.objects.filter(
            username=username,
            ip_address=ip_address,
            timestamp__gte=fifteen_mins_ago
        ).count()

        if failures >= 5:
            messages.error(request, 'Too many failed login attempts. Your account is temporarily locked. Please try again in 15 minutes.')
            return render(request, self.template_name, self.get_context_data())

        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        # Log the failed attempt
        username = self.request.POST.get('username')
        ip_address = self.get_client_ip()
        LoginAttempt.objects.create(username=username, ip_address=ip_address)
        return super().form_invalid(form)

class ApophiaLogoutView(LogoutView):
    template_name = 'apophia/logout.html'

class ApophiaPasswordChangeView(PasswordChangeView):
    template_name = 'apophia/password_change.html'
    success_url = reverse_lazy('password_change_done')

class ApophiaPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'apophia/password_change_done.html'

@login_required
def dashboard(request):
    return render(request, 'apophia/dashboard.html')

@user_passes_test(lambda u: u.is_staff)
def staff_directory(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'apophia/staff_directory.html', {'users': users})

class ApophiaPasswordResetView(PasswordResetView):
    template_name = 'apophia/password_reset_form.html'
    email_template_name = 'apophia/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

class ApophiaPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'apophia/password_reset_done.html'

class ApophiaPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'apophia/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class ApophiaPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'apophia/password_reset_complete.html'
