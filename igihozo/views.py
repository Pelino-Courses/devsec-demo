from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import AccountUpdateForm, LoginForm, RegistrationForm, StyledPasswordChangeForm


class HomeView(TemplateView):
    template_name = "igihozo/home.html"


class RegisterView(FormView):
    template_name = "igihozo/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("igihozo:account")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("igihozo:account")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Your account has been created and you are now signed in.")
        return super().form_valid(form)


class UserLoginView(LoginView):
    template_name = "igihozo/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "Welcome back. You have signed in successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_redirect_url() or str(reverse_lazy("igihozo:account"))


class UserLogoutView(LogoutView):
    template_name = "igihozo/logged_out.html"


class AccountView(LoginRequiredMixin, FormView):
    template_name = "igihozo/account.html"
    form_class = AccountUpdateForm
    success_url = reverse_lazy("igihozo:account")
    login_url = reverse_lazy("igihozo:login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.request.user.profile
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "igihozo/password_change_form.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("igihozo:password_change_done")
    login_url = reverse_lazy("igihozo:login")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been updated.")
        return super().form_valid(form)


class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "igihozo/password_change_done.html"
    login_url = reverse_lazy("igihozo:login")
