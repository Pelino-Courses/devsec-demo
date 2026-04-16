import logging
import os

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
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render, resolve_url
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, TemplateView

from .authorization import is_instructor
from .forms import ProfileUploadForm, StudentRegistrationForm
from .models import Profile

logger = logging.getLogger('uwase05.audit')


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

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(
            'auth event=registration username=%s email=%s',
            self.object.username,
            self.object.email,
        )
        return response


class UserLoginView(LoginThrottlingMixin, LoginView):
    template_name = 'uwase05/login.html'
    redirect_authenticated_user = True
    redirect_field_name = 'next'

    def get_success_url(self):
        redirect_url = self.get_redirect_url()
        if redirect_url and url_has_allowed_host_and_scheme(
            redirect_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect_url
        return resolve_url(settings.LOGIN_REDIRECT_URL)


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('uwase05:login')
    redirect_field_name = 'next'

    def get_next_page(self):
        next_page = super().get_next_page()
        if next_page and url_has_allowed_host_and_scheme(
            next_page,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_page
        return self.next_page


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'uwase05/password_change.html'
    success_url = reverse_lazy('uwase05:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(
            'auth event=password_changed username=%s ip=%s',
            self.request.user.username,
            self.request.META.get('REMOTE_ADDR', 'unknown'),
        )
        return response


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'uwase05/password_change_done.html'


class UserPasswordResetView(PasswordResetView):
    template_name = 'uwase05/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('uwase05:password_reset_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(
            'auth event=password_reset_requested email=%s ip=%s',
            form.cleaned_data.get('email'),
            self.request.META.get('REMOTE_ADDR', 'unknown'),
        )
        return response


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'uwase05/password_reset_done.html'


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'uwase05/password_reset_confirm.html'
    success_url = reverse_lazy('uwase05:password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        if hasattr(form, 'user') and form.user is not None:
            username = form.user.username
        else:
            username = 'unknown'
        logger.info(
            'auth event=password_reset_completed username=%s ip=%s',
            username,
            self.request.META.get('REMOTE_ADDR', 'unknown'),
        )
        return response


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


def _content_type_from_name(filename):
    if filename.lower().endswith(('.jpg', '.jpeg')):
        return 'image/jpeg'
    if filename.lower().endswith('.png'):
        return 'image/png'
    if filename.lower().endswith('.gif'):
        return 'image/gif'
    if filename.lower().endswith('.pdf'):
        return 'application/pdf'
    return 'text/plain'


@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    success_message = None

    if request.method == 'POST':
        form = ProfileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.cleaned_data.get('avatar')
            document = form.cleaned_data.get('document')
            if avatar:
                profile.avatar = avatar
            if document:
                profile.document = document
            if avatar or document:
                profile.save()
                success_message = 'File uploads were saved successfully.'
    else:
        form = ProfileUploadForm()

    return render(
        request,
        'uwase05/profile.html',
        {
            'profile': profile,
            'form': form,
            'success_message': success_message,
        },
    )


@login_required
def profile_avatar(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.avatar:
        raise Http404()
    return FileResponse(
        profile.avatar.open('rb'),
        content_type=_content_type_from_name(profile.avatar.name),
    )


@login_required
def profile_document(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if not profile.document:
        raise Http404()
    response = FileResponse(
        profile.document.open('rb'),
        content_type=_content_type_from_name(profile.document.name),
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{os.path.basename(profile.document.name)}"'
    )
    return response
