from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import UserProfile, AuditLog
from .utils import record_audit_log

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, role='viewer')
            
            # AUDIT LOG: Registration
            record_audit_log('registration', request, user=user, details="New user created")
            
            messages.success(request, 'Account created! Please login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username', '')
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # AUDIT LOG: Login Success
            record_audit_log('login_success', request, user=user)
            
            return redirect('profile')
        else:
            # AUDIT LOG: Login Failure
            record_audit_log('login_failure', request, username_attempted=username, details="Invalid credentials")
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        
        # AUDIT LOG: Logout
        if user.is_authenticated:
            record_audit_log('logout', request, user=user)
            
    return redirect('login')

@login_required
def profile_view(request):
    logs = AuditLog.objects.filter(user=request.user)[:10]
    return render(request, 'accounts/profile.html', {'logs': logs})

def is_admin(user):
    return hasattr(user, 'userprofile') and user.userprofile.role == 'admin'

@login_required
@user_passes_test(is_admin)
def update_role(request, user_id):
    """Admin-only view to change user roles with audit logging."""
    from django.contrib.auth.models import User
    target_user = User.objects.get(pk=user_id)
    target_profile = target_user.userprofile
    
    if request.method == 'POST':
        old_role = target_profile.role
        new_role = request.POST.get('role')
        if new_role in [choice[0] for choice in UserProfile.ROLE_CHOICES]:
            target_profile.role = new_role
            target_profile.save()
            
            # AUDIT LOG: Privilege Change
            record_audit_log(
                'privilege_change', 
                request, 
                user=request.user, 
                details=f"Changed user {target_user.username} role: {old_role} -> {new_role}"
            )
            
            messages.success(request, f"Updated {target_user.username} to {new_role}")
    
    return redirect('profile')
