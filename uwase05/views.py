from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
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


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'uwase05/password_change.html'
    success_url = reverse_lazy('uwase05:password_change_done')


class PasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    template_name = 'uwase05/password_change_done.html'


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
