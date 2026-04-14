from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, UserPasswordChangeForm


@require_http_methods(["GET", "POST"])
def register_view(request):
    """Handle user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Account created successfully! Welcome, {user.username}.'
            )
            login(request, user)
            return redirect('mucyo_aime_maxime:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'mucyo_aime_maxime/register.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('mucyo_aime_maxime:profile')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('mucyo_aime_maxime:profile')
            else:
                messages.error(
                    request,
                    'Invalid username or password. Please try again.'
                )
    else:
        form = UserLoginForm()
    
    return render(request, 'mucyo_aime_maxime/login.html', {'form': form})


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('mucyo_aime_maxime:login')


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def profile_view(request):
    """Display and handle user profile updates."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('mucyo_aime_maxime:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'mucyo_aime_maxime/profile.html', {'form': form})


@login_required(login_url='mucyo_aime_maxime:login')
@require_http_methods(["GET", "POST"])
def password_change_view(request):
    """Handle user password change."""
    if request.method == 'POST':
        form = UserPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Your password has been changed successfully.'
            )
            return redirect('mucyo_aime_maxime:profile')
    else:
        form = UserPasswordChangeForm(request.user)
    
    return render(request, 'mucyo_aime_maxime/password_change.html', {'form': form})
