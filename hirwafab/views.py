from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .forms import RegistrationForm, LoginForm, PasswordChangeForm, UserProfileForm
from .models import UserProfile


@require_http_methods(["GET", "POST"])
@csrf_protect
def register(request):
    """
    Handle user registration.
    
    GET: Display registration form
    POST: Process registration and create new user account
    """
    if request.user.is_authenticated:
        return redirect('hirwafab:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-assign user to 'students' group for RBAC
            try:
                students_group = Group.objects.get(name='students')
                user.groups.add(students_group)
            except Group.DoesNotExist:
                pass  # Group will be created via management command
            
            messages.success(
                request,
                f'Account created successfully! Welcome {user.username}. You can now log in.'
            )
            return redirect('hirwafab:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'hirwafab/register.html', context)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    Handle user login.
    
    GET: Display login form
    POST: Authenticate user and create session
    """
    if request.user.is_authenticated:
        return redirect('hirwafab:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                # Ensure user is in students group — handles accounts created
                # before RBAC migration ran.
                if not user.groups.exists():
                    try:
                        user.groups.add(Group.objects.get(name='students'))
                    except Group.DoesNotExist:
                        pass
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('hirwafab:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    context = {'form': form}
    return render(request, 'hirwafab/login.html', context)


@login_required(login_url='hirwafab:login')
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Handle user logout.
    Clears the user session and redirects to login page.
    """
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('hirwafab:login')

    return render(request, 'hirwafab/logout_confirm.html')


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_dashboard', raise_exception=True)
def dashboard(request):
    """
    Protected dashboard page - requires authentication and view_dashboard permission.
    Displays user's profile information and welcome message.
    """
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'hirwafab/dashboard.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.change_own_password', raise_exception=True)
@require_http_methods(["GET", "POST"])
def change_password(request):
    """
    Handle password change for authenticated users.
    Requires change_own_password permission.
    
    GET: Display password change form
    POST: Process password change with validation
    """
    # Object-level ownership check: password changes must only ever apply to
    # the currently authenticated user — never to a user resolved from
    # external input.
    if not request.user.is_authenticated:
        raise PermissionDenied

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('hirwafab:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = PasswordChangeForm(request.user)

    context = {'form': form}
    return render(request, 'hirwafab/change_password.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_own_profile', raise_exception=True)
@require_http_methods(["GET", "POST"])
def profile(request):
    """
    Handle user profile view and updates.
    Requires view_own_profile permission.
    
    GET: Display user profile
    POST: Update profile information
    """
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    # Object-level ownership check: the profile being edited must belong to
    # the currently authenticated user. This prevents IDOR if the profile
    # object is ever resolved through a different path.
    if user_profile.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('hirwafab:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserProfileForm(instance=user_profile)

    context = {
        'form': form,
        'profile': user_profile,
    }
    return render(request, 'hirwafab/profile.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_user_directory', raise_exception=True)
def user_directory(request):
    """
    Public user directory - shows all users with basic information.
    Requires view_user_directory permission (student and above).
    """
    users = UserProfile.objects.all().select_related('user')
    
    context = {
        'users': users,
        'is_public_view': True,
    }
    return render(request, 'hirwafab/user_directory.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_all_profiles', raise_exception=True)
def user_directory_full(request):
    """
    Full user directory with detailed information - instructor/admin only.
    Requires view_all_profiles permission (instructors and above).
    Shows email, bio, avatar, and registration date.
    """
    users = UserProfile.objects.all().select_related('user')
    
    context = {
        'users': users,
        'is_full_view': True,
    }
    return render(request, 'hirwafab/user_directory_full.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_all_profiles', raise_exception=True)
def view_user_profile(request, user_id):
    """
    View another user's profile - instructor/admin only.
    Requires view_all_profiles permission.
    Can only view other users' full profiles, not their own (use profile() for that).
    """
    # Redirect to own profile page when requesting own user_id
    if request.user.id == user_id:
        return redirect('hirwafab:profile')

    user_profile = get_object_or_404(UserProfile, user_id=user_id)

    # Object-level check: even after the role-level @permission_required above,
    # explicitly verify the requesting user is authorised to view this specific
    # profile object. Only instructors (view_all_profiles) and superusers may
    # view another user's full profile.
    if not (request.user.has_perm('hirwafab.view_all_profiles') or request.user.is_superuser):
        raise PermissionDenied

    context = {
        'profile': user_profile,
        'is_other_profile': True,
    }
    return render(request, 'hirwafab/view_user_profile.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.view_user_activity', raise_exception=True)
def user_activity(request):
    """
    View user activity and statistics - instructor only.
    Requires view_user_activity permission.
    Shows registration dates, last login info, and activity summary.
    """
    users = UserProfile.objects.all().select_related('user').order_by('-created_at')
    
    # Calculate statistics
    total_users = users.count()
    recent_registrations = users[:10]  # Last 10 registered
    
    context = {
        'users': users,
        'total_users': total_users,
        'recent_registrations': recent_registrations,
    }
    return render(request, 'hirwafab/user_activity.html', context)


@login_required(login_url='hirwafab:login')
@permission_required('hirwafab.download_reports', raise_exception=True)
def reports(request):
    """
    Generate and download user reports - instructor only.
    Requires download_reports permission.
    Provides export of user data in various formats.
    """
    users = UserProfile.objects.all().select_related('user')
    user_data = []
    
    for profile in users:
        user_data.append({
            'username': profile.user.username,
            'email': profile.user.email,
            'first_name': profile.user.first_name,
            'last_name': profile.user.last_name,
            'registered': profile.created_at,
            'bio': profile.bio,
        })
    
    context = {
        'user_count': users.count(),
        'user_data': user_data,
    }
    return render(request, 'hirwafab/reports.html', context)
