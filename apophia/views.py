from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView
from django.contrib import messages
from django.urls import reverse_lazy

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
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'apophia/profile.html', context)

class ApophiaLoginView(LoginView):
    template_name = 'apophia/login.html'
    redirect_authenticated_user = True

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
