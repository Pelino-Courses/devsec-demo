from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import render
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .authz import user_is_privileged
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_privileged_user"] = user_is_privileged(self.request.user)
        context["role_labels"] = self.get_role_labels()
        return context

    def get_role_labels(self):
        labels = []
        if self.request.user.is_superuser:
            labels.append("Administrator")
        elif self.request.user.is_staff:
            labels.append("Staff")

        group_names = set(self.request.user.groups.values_list("name", flat=True))
        if "instructors" in group_names:
            labels.append("Instructor")
        if "students" in group_names:
            labels.append("Student")
        return labels or ["Authenticated user"]


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


class PrivilegedAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("igihozo:login")

    def test_func(self):
        return user_is_privileged(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, "403.html", status=403)
        return super().handle_no_permission()


class PrivilegedDashboardView(PrivilegedAccessMixin, TemplateView):
    template_name = "igihozo/privileged_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = User.objects.select_related("profile").prefetch_related("groups").order_by(
            "username"
        )
        context["role_summary"] = {
            "anonymous_visitors": "Can browse public pages only and cannot access account features.",
            "authenticated_users": "Can manage their own account, profile, session, and password.",
            "privileged_users": "Can access the privileged dashboard and review registered users.",
        }
        return context


def permission_denied_view(request, exception, template_name="403.html"):
    return render(request, template_name, status=403)
