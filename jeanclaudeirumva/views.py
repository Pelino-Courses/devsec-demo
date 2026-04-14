from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import RegistrationForm, LoginForm, PasswordChangeForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('jeanclaudeirumva:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
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
    return render(request, 'jeanclaudeirumva/dashboard.html', {'user': request.user})


@login_required(login_url='jeanclaudeirumva:login')
def profile_view(request):
    return render(request, 'jeanclaudeirumva/profile.html', {'user': request.user})


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


@login_required(login_url='jeanclaudeirumva:login')
@require_POST
def update_profile_ajax(request):
    """
    AJAX endpoint for profile updates.
    Protected by CSRF middleware and @require_POST.
    The client must send the csrfmiddlewaretoken in the request.
    """
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
    user = request.user
    user.email = email
    user.save()
    return JsonResponse({'success': True, 'email': user.email})