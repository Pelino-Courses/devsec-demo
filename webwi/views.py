import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView

from .forms import LoginForm, PasswordResetRequestForm, PasswordResetSetForm, PasswordUpdateForm, ProfileForm, RegistrationForm
from .models import LoginAttempt, MAX_FAILED_ATTEMPTS, Profile


class PrivilegedAccessMixin(LoginRequiredMixin):
    """Allow access only to staff/superusers or users with explicit RBAC permission."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        is_privileged = (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.has_perm('webwi.view_user_directory')
        )
        if not is_privileged:
            raise PermissionDenied('You do not have permission to access this area.')
        return super().dispatch(request, *args, **kwargs)


class OwnershipRequiredMixin(LoginRequiredMixin):
    """Enforce object-level ownership: the fetched object's user must be the current user.

    Prevents IDOR by refusing access whenever the object returned by get_object()
    belongs to a different account.  Apply this mixin to any view that looks up
    a user-owned resource so the protection is explicit and auditable.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if not hasattr(obj, 'user') or obj.user_id != self.request.user.pk:
            raise PermissionDenied('You do not have permission to access this resource.')
        return obj


class UserRegistrationView(FormView):
    form_class = RegistrationForm
    template_name = 'webwi/register.html'
    success_url = reverse_lazy('webwi:login')
    extra_context = {'page_title': 'Create Account'}

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Account created successfully. You can now log in.')
        return super().form_valid(form)


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = 'webwi/login.html'
    extra_context = {'page_title': 'Welcome Back'}

    def post(self, request, *args, **kwargs):
        # Check lockout before processing credentials so the authentication
        # backend is never called while the account is in cooldown.
        username = request.POST.get('username', '').strip()
        if username and LoginAttempt.is_locked(username):
            form = self.get_form()
            form.add_error(
                None,
                f'Too many failed attempts. This account is locked for 15 minutes.',
            )
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        # Record the failed attempt so the counter advances toward lockout.
        username = form.data.get('username', '').strip()
        if username:
            LoginAttempt.record(username, self.request.META.get('REMOTE_ADDR'))
        return super().form_invalid(form)

    def form_valid(self, form):
        # Successful login resets the counter for this account.
        LoginAttempt.clear(form.cleaned_data.get('username', ''))
        return super().form_valid(form)


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('webwi:login')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'webwi/dashboard.html'
    extra_context = {'page_title': 'Dashboard'}


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = PasswordUpdateForm
    template_name = 'webwi/password_change.html'
    success_url = reverse_lazy('webwi:password_change_done')
    extra_context = {'page_title': 'Change Password'}


class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'webwi/password_change_done.html'
    extra_context = {'page_title': 'Password Updated'}


class ProfileView(OwnershipRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'webwi/profile.html'
    success_url = reverse_lazy('webwi:profile')
    extra_context = {'page_title': 'My Profile'}

    def get_object(self, queryset=None):
        # Fetch the profile that belongs to the authenticated user only.
        # This eliminates the IDOR vector: no URL parameter, query string value,
        # or POST field can redirect this lookup to another user's profile row.
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        if profile.user_id != self.request.user.pk:
            raise PermissionDenied('You do not have permission to access this profile.')
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = form.save(user=self.request.user)
        messages.success(self.request, 'Your profile was updated successfully.')
        return redirect(self.get_success_url())


class UserDirectoryView(PrivilegedAccessMixin, TemplateView):
    template_name = 'webwi/user_directory.html'
    extra_context = {'page_title': 'User Directory'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_model = get_user_model()
        context['users'] = user_model.objects.order_by('username').select_related('profile')
        return context


class UserPasswordResetView(PasswordResetView):
    form_class = PasswordResetRequestForm
    template_name = 'webwi/password_reset.html'
    email_template_name = 'webwi/password_reset_email.txt'
    subject_template_name = 'webwi/password_reset_subject.txt'
    success_url = reverse_lazy('webwi:password_reset_done')
    extra_context = {'page_title': 'Reset Password'}


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'webwi/password_reset_done.html'
    extra_context = {'page_title': 'Check Your Email'}


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = PasswordResetSetForm
    template_name = 'webwi/password_reset_confirm.html'
    success_url = reverse_lazy('webwi:password_reset_complete')
    extra_context = {'page_title': 'Set New Password'}


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'webwi/password_reset_complete.html'
    extra_context = {'page_title': 'Password Reset Complete'}


@login_required
@require_POST
def quick_display_name_update(request):
    """AJAX endpoint to update the authenticated user's display name."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    display_name = data.get('display_name', '').strip()[:150]
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.display_name = display_name
    profile.save(update_fields=['display_name'])
    return JsonResponse({'display_name': profile.display_name})


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('webwi:dashboard')
    return redirect('webwi:login')
