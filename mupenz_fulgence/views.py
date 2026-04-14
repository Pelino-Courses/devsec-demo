from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import ProfileUpdateForm, RegistrationForm
from .models import Profile


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterView(CreateView):
    """
    Handles new user sign-up.
    Redirects already-authenticated users straight to the dashboard.
    On success, redirects to the login page with a confirmation message.
    """
    model = User
    form_class = RegistrationForm
    template_name = 'mupenz_fulgence/registration/register.html'
    success_url = reverse_lazy('mupenz_fulgence:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse_lazy('mupenz_fulgence:dashboard'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Account created for "{self.object.username}". You can now sign in.',
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Registration failed. Please correct the errors below.',
        )
        return super().form_invalid(form)


# ---------------------------------------------------------------------------
# Login / Logout — thin wrappers around Django's built-in auth views
# ---------------------------------------------------------------------------

class UserLoginView(auth_views.LoginView):
    """
    Authenticates users via Django's built-in LoginView.
    Redirects already-authenticated users away from the login page.
    """
    template_name = 'mupenz_fulgence/registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        name = user.get_short_name() or user.username
        messages.success(self.request, f'Welcome back, {name}!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Invalid username or password. Please try again.',
        )
        return super().form_invalid(form)


class UserLogoutView(auth_views.LogoutView):
    """
    Logs the user out (POST only — Django 5+ requirement).
    Adds a farewell message before the session is flushed.
    The message survives because FallbackStorage writes to a cookie first.
    """
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You have been logged out. See you soon!')
        return super().post(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Dashboard (protected)
# ---------------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Home page for authenticated users — shows account and profile summary.
    """
    template_name = 'mupenz_fulgence/dashboard.html'
    login_url = reverse_lazy('mupenz_fulgence:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get_or_create is a safety net for superusers created before the app
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        return context


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Lets the authenticated user view and update their profile.
    Always operates on the currently logged-in user's profile.
    """
    model = Profile
    form_class = ProfileUpdateForm
    template_name = 'mupenz_fulgence/profile.html'
    login_url = reverse_lazy('mupenz_fulgence:login')
    success_url = reverse_lazy('mupenz_fulgence:profile')

    def get_object(self, queryset=None):
        # Safety net: create the profile on-the-fly if it doesn't exist
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Update failed. Please correct the errors below.')
        return super().form_invalid(form)


# ---------------------------------------------------------------------------
# Password Change
# ---------------------------------------------------------------------------

class UserPasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    """
    Allows authenticated users to change their password.
    Django's built-in implementation calls update_session_auth_hash()
    automatically, so the user stays logged in after the change.
    """
    template_name = 'mupenz_fulgence/registration/password_change.html'
    login_url = reverse_lazy('mupenz_fulgence:login')
    success_url = reverse_lazy('mupenz_fulgence:dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Password change failed. Please review the errors below.',
        )
        return super().form_invalid(form)
