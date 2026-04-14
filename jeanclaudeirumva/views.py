from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from .forms import RegistrationForm, LoginForm, PasswordChangeForm
from .roles import ROLE_STUDENT, get_user_role, setup_roles
from .decorators import instructor_required, admin_required

def register_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign default student role on registration
            setup_roles()
            try:
                student_group = Group.objects.get(name=ROLE_STUDENT)
                user.groups.add(student_group)
            except Group.DoesNotExist:
                pass
            login(request, user)
            messages.success(request, "Account created successfully! Welcome!")
            return redirect('jeanclaudeirumva:dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegistrationForm()
    return render(request, 'jeanclaudeirumva/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('jeanclaudeirumva:dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'jeanclaudeirumva/login.html', {'form': form})


@login_required(login_url='jeanclaudeirumva:login')
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('jeanclaudeirumva:login')
    return render(request, 'jeanclaudeirumva/logout_confirm.html')


@login_required(login_url='jeanclaudeirumva:login')
def dashboard_view(request):
    role = get_user_role(request.user)
    return render(request, 'jeanclaudeirumva/dashboard.html', {
        'user': request.user,
        'role': role,
    })


@login_required(login_url='jeanclaudeirumva:login')
def profile_view(request):
    role = get_user_role(request.user)
    return render(request, 'jeanclaudeirumva/profile.html', {
        'user': request.user,
        'role': role,
    })


@login_required(login_url='jeanclaudeirumva:login')
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            if not user.check_password(old_password):
                messages.error(request, "Old password is incorrect.")
            else:
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('jeanclaudeirumva:dashboard')
    else:
        form = PasswordChangeForm()
    return render(request, 'jeanclaudeirumva/password_change.html', {'form': form})


@instructor_required
def instructor_area_view(request):
    """Only instructors and admins can access this area."""
    students = User.objects.filter(groups__name=ROLE_STUDENT)
    return render(request, 'jeanclaudeirumva/instructor_area.html', {
        'students': students,
    })


@admin_required
def admin_area_view(request):
    """Only admins can access this area."""
    all_users = User.objects.all()
    return render(request, 'jeanclaudeirumva/admin_area.html', {
        'all_users': all_users,
    })