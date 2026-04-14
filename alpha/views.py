from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from .forms import CustomUserCreationForm, ProfileUpdateForm
from .models import UserProfile

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'alpha/register.html', {'form': form})

class RateLimitedLoginView(LoginView):
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            ip = request.META.get('REMOTE_ADDR')
            username = request.POST.get('username', '')
            key = f'login_attempts_{username}_{ip}'
            attempts = cache.get(key, 0)
            if attempts >= 5:
                return render(request, 'alpha/login_locked.html', status=429)
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        ip = self.request.META.get('REMOTE_ADDR')
        username = self.request.POST.get('username', '')
        key = f'login_attempts_{username}_{ip}'
        attempts = cache.get(key, 0)
        cache.set(key, attempts + 1, timeout=900)
        return super().form_invalid(form)

    def form_valid(self, form):
        ip = self.request.META.get('REMOTE_ADDR')
        username = form.cleaned_data.get('username')
        key = f'login_attempts_{username}_{ip}'
        cache.delete(key)
        return super().form_valid(form)

@login_required
def profile(request):
    return render(request, 'alpha/profile.html')

@login_required
def update_profile(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    target_profile = get_object_or_404(UserProfile, user=target_user)

    # Object-Level Access Control (Prevent IDOR)
    if request.user.id != target_user.id and not request.user.has_perm('alpha.can_view_dashboard'):
        return HttpResponseForbidden("You do not have permission to edit this profile.")

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=target_profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=target_profile)

    return render(request, 'alpha/profile_update.html', {'form': form, 'target_user': target_user})

@login_required
def protected_view(request):
    return render(request, 'alpha/protected.html')

@login_required
@permission_required('alpha.can_view_dashboard', raise_exception=True)
def instructor_dashboard(request):
    return render(request, 'alpha/dashboard.html')
