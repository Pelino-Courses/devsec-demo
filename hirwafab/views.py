from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
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
def dashboard(request):
    """
    Protected dashboard page - requires authentication.
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
@require_http_methods(["GET", "POST"])
def change_password(request):
    """
    Handle password change for authenticated users.
    
    GET: Display password change form
    POST: Process password change with validation
    """
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
@require_http_methods(["GET", "POST"])
def profile(request):
    """
    Handle user profile view and updates.
    
    GET: Display user profile
    POST: Update profile information
    """
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

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
