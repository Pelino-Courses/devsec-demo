from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.core.cache import cache
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, TemplateView

from .authorization import is_instructor
from .forms import StudentRegistrationForm
from .models import Profile


class HomeView(TemplateView):
    template_name = 'uwase05/home.html'


class LoginThrottlingMixin:
    max_failed_attempts = 5
    lockout_timeout = 300
    lockout_message = (
        'Too many failed login attempts. Please try again in 5 minutes.'
    )

    def get_client_ip(self):
        return self.request.META.get('REMOTE_ADDR', 'unknown')

    def get_username(self):
        return self.request.POST.get('username', '').strip().lower() or 'unknown'

    def get_attempt_cache_key(self):
        return f'login_throttle:attempts:{self.get_client_ip()}:{self.get_username()}'

    def get_lockout_cache_key(self):
        return f'login_throttle:locked:{self.get_client_ip()}:{self.get_username()}'

    def is_locked_out(self):
        return cache.get(self.get_lockout_cache_key(), False)

    def post(self, request, *args, **kwargs):
        if self.is_locked_out():
            form = self.get_form()
            form.add_error(None, self.lockout_message)
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        if self.request.POST.get('username') and self.request.POST.get('password'):
            attempts = cache.get(self.get_attempt_cache_key(), 0) + 1
            cache.set(self.get_attempt_cache_key(), attempts, self.lockout_timeout)
            if attempts >= self.max_failed_attempts:
                cache.set(self.get_lockout_cache_key(), True, self.lockout_timeout)
                form.add_error(None, self.lockout_message)

        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self.get_attempt_cache_key())
        cache.delete(self.get_lockout_cache_key())
        return super().form_valid(form)


class RegisterView(CreateView):
    template_name = 'uwase05/register.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('uwase05:login')


class UserLoginView(LoginThrottlingMixin, LoginView):
    template_name = 'uwase05/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('uwase05:login')


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'uwase05/password_change.html'
    success_url = reverse_lazy('uwase05:password_change_done')


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'uwase05/password_change_done.html'


class UserPasswordResetView(PasswordResetView):
    template_name = 'uwase05/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('uwase05:password_reset_done')


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'uwase05/password_reset_done.html'


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'uwase05/password_reset_confirm.html'
    success_url = reverse_lazy('uwase05:password_reset_complete')


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'uwase05/password_reset_complete.html'


@method_decorator(login_required, name='dispatch')
class InstructorDashboardView(UserPassesTestMixin, TemplateView):
    template_name = 'uwase05/instructor_dashboard.html'
    raise_exception = True

    def test_func(self):
        return is_instructor(self.request.user)


@login_required
def dashboard(request):
    return render(request, 'uwase05/dashboard.html')


@login_required
def profile(request):
    # Load or create only the profile belonging to the authenticated user.
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'uwase05/profile.html', {'profile': profile})
