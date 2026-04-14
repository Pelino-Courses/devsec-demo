from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from .forms import ProfileUpdateForm, CustomUserCreationForm, ProfileDataForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from .models import Profile

def register(request):
    """User registration view using custom form"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {user.username}!')
            return redirect('Munyabugingo:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'olivier/register.html', {'form': form})

@login_required
def dashboard(request):
    """Protected dashboard view"""
    return render(request, 'olivier/dashboard.html', {
        'user': request.user
    })

@login_required
def profile(request):
    """User profile view with dual form update"""
    if request.method == 'POST':
        u_form = ProfileUpdateForm(request.POST, instance=request.user)
        p_form = ProfileDataForm(request.POST, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('Munyabugingo:profile')
    else:
        u_form = ProfileUpdateForm(instance=request.user)
        p_form = ProfileDataForm(instance=request.user.profile)
    
    return render(request, 'olivier/profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })

@login_required
def profile_detail(request, pk):
    """Secure profile detail view with IDOR protection"""
    profile_obj = get_object_or_404(Profile, pk=pk)
    
    # IDOR check: Verify owner or privileged access
    if profile_obj.user != request.user and not request.user.has_perm('Munyabugingo.can_view_admin_dashboard'):
        raise PermissionDenied
        
    return render(request, 'olivier/profile_detail.html', {
        'profile': profile_obj
    })

@permission_required('Munyabugingo.can_view_admin_dashboard', raise_exception=True)
def admin_dashboard(request):
    """Admin dashboard view for user management"""
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    return render(request, 'olivier/admin_dashboard.html', {'all_users': users})

def get_client_ip(request):
    """Helper to extract IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class SecureLoginView(LoginView):
    """Login view with brute-force protection using IP-based throttling"""
    template_name = 'olivier/login.html'
    max_attempts = 5
    lockout_time = 900  # 15 minutes in seconds

    def dispatch(self, request, *args, **kwargs):
        ip = get_client_ip(request)
        lockout_key = f'lockout_{ip}'
        
        if cache.get(lockout_key):
            messages.error(request, 'Your IP has been temporarily blocked due to too many failed login attempts. Please try again in 15 minutes.')
            return render(request, self.template_name, {'form': self.get_form()})
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Successful login: reset attempts for this IP
        ip = get_client_ip(self.request)
        cache.delete(f'attempts_{ip}')
        return super().form_valid(form)

    def form_invalid(self, form):
        # Failed attempt: increment counter
        ip = get_client_ip(self.request)
        attempts_key = f'attempts_{ip}'
        attempts = cache.get(attempts_key, 0) + 1
        
        if attempts >= self.max_attempts:
            # Trigger lockout
            cache.set(f'lockout_{ip}', True, self.lockout_time)
            messages.error(self.request, 'Too many failed attempts. Your IP is now blocked for 15 minutes.')
        else:
            cache.set(attempts_key, attempts, 300) # Reset window of 5 minutes
            messages.error(self.request, f'Invalid credentials. Attempt {attempts} of {self.max_attempts}.')
            
        return super().form_invalid(form)

@login_required
def toggle_like(request):
    """Secure AJAX endpoint for liking content with CSRF protection"""
    if request.method == 'POST':
        # In a real app, this would update a database record
        # For this lab, we'll just simulate a successful state change
        action = request.POST.get('action')
        content_id = request.POST.get('content_id')
        
        # Simulate validation
        if not content_id:
            return JsonResponse({'status': 'error', 'message': 'Missing content ID'}, status=400)
            
        return JsonResponse({
            'status': 'success',
            'action': action,
            'content_id': content_id,
            'message': f'State change successful for {content_id}'
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)