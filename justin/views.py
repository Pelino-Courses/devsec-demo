from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponseForbidden
from .forms import RegisterForm
from .models import Profile, Role


def privileged_required(view_func):
    """Decorator requiring user to have privileged role."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.profile.is_privileged:
                return render(request, 'justin/403.html', {'message': 'This action requires elevated privileges.'}, status=403)
        except Profile.DoesNotExist:
            return render(request, 'justin/403.html', {'message': 'Profile not found.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator requiring user to have admin role."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        try:
            if not request.user.profile.is_admin:
                return render(request, 'justin/403.html', {'message': 'This action requires administrator privileges.'}, status=403)
        except Profile.DoesNotExist:
            return render(request, 'justin/403.html', {'message': 'Profile not found.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(allowed_roles):
    """Decorator requiring user to have one of the specified roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                if request.user.profile.role not in allowed_roles:
                    return render(request, 'justin/403.html', {'message': 'You do not have permission to access this resource.'}, status=403)
            except Profile.DoesNotExist:
                return render(request, 'justin/403.html', {'message': 'Profile not found.'}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def home_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    return render(request, 'justin/index.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Registration successful")
            return redirect('profile')
    else:
        form = RegisterForm()

    return render(request, 'justin/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            if not remember_me:
                request.session.set_expiry(0)
            
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('profile')
        else:
            messages.error(request, "Invalid username or password")
    else:
        form = AuthenticationForm()

    return render(request, 'justin/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully")
    return redirect('login')


@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    return render(request, 'justin/profile.html', {'profile': profile})


@login_required
def update_profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        profile, _ = Profile.objects.get_or_create(user=user)
        
        image_url = request.POST.get('image_url', '')
        profile.image_url = image_url
        profile.bio = request.POST.get('bio', '')
        profile.save()
        
        messages.success(request, "Profile updated successfully")
        return redirect('profile')
    
    return render(request, 'justin/update_profile.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully")
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'justin/change_password.html', {'form': form})


@privileged_required
def admin_dashboard(request):
    """Dashboard for privileged users (instructors, staff, admins)."""
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'justin/admin_dashboard.html', {'profiles': profiles})


@admin_required
def user_management(request):
    """User management panel for administrators only."""
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'justin/user_management.html', {'profiles': profiles})


@admin_required
def change_user_role(request, user_id):
    """Change a user's role - admin only."""
    target_user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in [role[0] for role in Role.choices]:
            target_profile, _ = Profile.objects.get_or_create(user=target_user)
            target_profile.role = new_role
            target_profile.save()
            messages.success(request, f"Role updated for {target_user.username}")
        return redirect('user_management')
    
    return render(request, 'justin/change_user_role.html', {'target_user': target_user})


@privileged_required
def view_all_profiles(request):
    """View all user profiles - privileged users only."""
    profiles = Profile.objects.select_related('user').all()
    return render(request, 'justin/all_profiles.html', {'profiles': profiles})