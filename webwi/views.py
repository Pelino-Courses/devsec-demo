from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView

from .forms import LoginForm, PasswordUpdateForm, ProfileForm, RegistrationForm
from .models import Profile


class UserRegistrationView(FormView):
	form_class = RegistrationForm
	template_name = 'webwi/register.html'
	success_url = reverse_lazy('webwi:login')

	def form_valid(self, form):
		form.save()
		messages.success(self.request, 'Account created successfully. You can now log in.')
		return super().form_valid(form)


class UserLoginView(LoginView):
	form_class = LoginForm
	template_name = 'webwi/login.html'


class UserLogoutView(LogoutView):
	next_page = reverse_lazy('webwi:login')


class DashboardView(LoginRequiredMixin, TemplateView):
	template_name = 'webwi/dashboard.html'


class UserPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
	form_class = PasswordUpdateForm
	template_name = 'webwi/password_change.html'
	success_url = reverse_lazy('webwi:password_change_done')


class UserPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
	template_name = 'webwi/password_change_done.html'


class ProfileView(LoginRequiredMixin, UpdateView):
	model = Profile
	form_class = ProfileForm
	template_name = 'webwi/profile.html'
	success_url = reverse_lazy('webwi:profile')

	def get_object(self, queryset=None):
		profile, _ = Profile.objects.get_or_create(user=self.request.user)
		return profile

	def form_valid(self, form):
		messages.success(self.request, 'Your profile was updated successfully.')
		return super().form_valid(form)


def home_redirect(request):
	if request.user.is_authenticated:
		return redirect('webwi:dashboard')
	return redirect('webwi:login')
