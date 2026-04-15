from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .authorization import is_instructor
from .forms import StudentRegistrationForm
from .models import Profile


class HomeView(TemplateView):
    template_name = 'uwase05/home.html'


class RegisterView(CreateView):
    template_name = 'uwase05/register.html'
    form_class = StudentRegistrationForm
    success_url = reverse_lazy('uwase05:login')


class UserLoginView(LoginView):
    template_name = 'uwase05/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('uwase05:login')


class UserPasswordChangeView(PasswordChangeView):
    template_name = 'uwase05/password_change.html'
    success_url = reverse_lazy('uwase05:password_change_done')


class PasswordChangeDoneView(TemplateView):
    template_name = 'uwase05/password_change_done.html'


class InstructorDashboardView(TemplateView):
    template_name = 'uwase05/instructor_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not is_instructor(request.user):
            raise PermissionDenied()
        return super().dispatch(request, *args, **kwargs)


@login_required
def dashboard(request):
    return render(request, 'uwase05/dashboard.html')


@login_required
def profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'uwase05/profile.html', {'profile': profile})
