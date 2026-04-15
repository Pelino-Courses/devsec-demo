from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from .forms import ProfileUpdateForm, CustomUserCreationForm, ProfileDataForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.urls import reverse
from .models import Profile
from .utils import get_safe_redirect_url, log_audit_event

def register(request):
    """User registration view using custom form with safe redirect handling"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            log_audit_event('USER_REGISTRATION', user=user, request=request)
            # Use safe redirect validation
            redirect_to = get_safe_redirect_url(request, reverse('Munyabugingo:dashboard'))
            return redirect(redirect_to)
        else:
            log_audit_event('USER_REGISTRATION', status='FAILURE', request=request, metadata={'errors': form.errors})
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
    """User profile view with dual form update and secure file handling"""
    if request.method == 'POST':
        u_form = ProfileUpdateForm(request.POST, instance=request.user)
        # Pass request.FILES for avatar upload
        p_form = ProfileDataForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            log_audit_event('PROFILE_UPDATE', user=request.user, request=request)
            messages.success(request, 'Your profile has been updated!')
            
            redirect_to = get_safe_redirect_url(request, reverse('Munyabugingo:profile'))
            return redirect(redirect_to)
    else:
        u_form = ProfileUpdateForm(instance=request.user)
        p_form = ProfileDataForm(instance=request.user.profile)
    
    return render(request, 'olivier/profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })

@login_required
def list_documents(request):
    """List documents belonging to the authenticated user"""
    from .models import Document
    documents = Document.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'olivier/documents.html', {'documents': documents})

@login_required
def upload_document(request):
    """Handle secure document upload"""
    from .forms import DocumentUploadForm
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.user = request.user
            document.save()
            log_audit_event('DOCUMENT_UPLOAD', user=request.user, request=request, metadata={'title': document.title})
            messages.success(request, 'Document uploaded successfully!')
            return redirect('Munyabugingo:list_documents')
    else:
        form = DocumentUploadForm()
    
    return render(request, 'olivier/upload_document.html', {'form': form})

@login_required
def download_document(request, pk):
    """Secure document download with ownership check (Prevent IDOR)"""
    from .models import Document
    from django.http import HttpResponse, FileResponse
    import os
    
    document = get_object_or_404(Document, pk=pk)
    
    # Secure Authorization Check
    if document.user != request.user and not request.user.has_perm('Munyabugingo.can_view_admin_dashboard'):
        log_audit_event('UNAUTHORIZED_DOWNLOAD_ATTEMPT', user=request.user, request=request, metadata={'document_id': pk})
        raise PermissionDenied
    
    # Serve file using FileResponse (better than manual path serving)
    # In production, this should ideally be handled by Nginx X-Accel-Redirect
    file_path = document.file.path
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        log_audit_event('DOCUMENT_DOWNLOAD', user=request.user, request=request, metadata={'document_id': pk})
        return response
    
    messages.error(request, 'File not found.')
    return redirect('Munyabugingo:list_documents')

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
    """Login view with brute-force protection and enforced redirect validation"""
    template_name = 'olivier/login.html'
    max_attempts = 5
    lockout_time = 900  # 15 minutes in seconds

    def get_success_url(self):
        """Explicitly enforce redirect safety using central utility"""
        return get_safe_redirect_url(self.request, super().get_success_url())

    def dispatch(self, request, *args, **kwargs):
        ip = get_client_ip(request)
        lockout_key = f'lockout_{ip}'
        
        if cache.get(lockout_key):
            log_audit_event('LOGIN_LOCKOUT', request=request, status='BLOCKED', metadata={'ip': ip})
            messages.error(request, 'Your IP has been temporarily blocked due to too many failed login attempts. Please try again in 15 minutes.')
            return render(request, self.template_name, {'form': self.get_form()})
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Successful login: reset attempts for this IP
        ip = get_client_ip(self.request)
        log_audit_event('LOGIN_SUCCESS', user=form.get_user(), request=self.request)
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
            log_audit_event('LOGIN_FAILURE', status='LOCKOUT_TRIGGERED', request=self.request, metadata={'username': form.data.get('username'), 'attempts': attempts})
            messages.error(self.request, 'Too many failed attempts. Your IP is now blocked for 15 minutes.')
        else:
            cache.set(attempts_key, attempts, 300) # Reset window of 5 minutes
            log_audit_event('LOGIN_FAILURE', status='FAILURE', request=self.request, metadata={'username': form.data.get('username'), 'attempt_count': attempts})
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

class AuditPasswordChangeView(auth_views.PasswordChangeView):
    """Subclassed to log successful password changes"""
    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit_event('PASSWORD_CHANGE', user=self.request.user, request=self.request)
        return response

class AuditPasswordResetView(auth_views.PasswordResetView):
    """Subclassed to log password reset requests"""
    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        log_audit_event('PASSWORD_RESET_REQUEST', request=self.request, metadata={'email': email})
        return super().form_valid(form)

class AuditPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Subclassed to log successful password reset completion"""
    def form_valid(self, form):
        response = super().form_valid(form)
        # self.user is established by the parent view from the token
        log_audit_event('PASSWORD_RESET_COMPLETE', user=self.user, request=self.request)
        return response