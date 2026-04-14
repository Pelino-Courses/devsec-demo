from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from .forms import ProfileUpdateForm, CustomUserCreationForm, ProfileDataForm
from django.contrib.auth import login
from django.contrib.auth.models import User

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

@permission_required('Munyabugingo.can_view_admin_dashboard', raise_exception=True)
def admin_dashboard(request):
    """Admin-only view to monitor all registered users"""
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'olivier/admin_dashboard.html', {
        'all_users': users
    })