from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db import transaction
from django.http import HttpResponseRedirect

from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    CustomPasswordChangeForm,
    UserProfileForm
)
from .models import UserProfile


# ============================================================================
# PUBLIC VIEWS
# ============================================================================

class HomeView(TemplateView):
    """
    Public home page view.
    
    This view displays the landing page available to all users.
    """
    template_name = 'aline_uwamahoro/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_students'] = User.objects.count()
        return context


class RegisterView(View):
    """
    User registration view.
    
    Handles GET (display form) and POST (process registration) requests.
    Creates both User and UserProfile objects atomically.
    
    Security considerations:
    - Uses Django's built-in password hashing
    - Validates unique email and student_id
    - CSRF protection enabled by default
    - Form validation prevents common vulnerabilities
    """
    
    template_name = 'aline_uwamahoro/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('aline_uwamahoro:login')
    
    def get(self, request, *args, **kwargs):
        """Display registration form."""
        if request.user.is_authenticated:
            return redirect('aline_uwamahoro:dashboard')
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        """Process registration form submission."""
        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # User and UserProfile are saved atomically via form.save()
                    user = form.save()
                    messages.success(
                        request,
                        f'Welcome, {user.username}! Your account has been created. Please log in.'
                    )
                    return redirect(self.success_url)
            except Exception as e:
                messages.error(request, f'An error occurred during registration. Please try again.')
                return render(request, self.template_name, {'form': form})
        
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    """
    User login view.
    
    Handles GET (display login form) and POST (authenticate user) requests.
    
    Security considerations:
    - Uses Django's authentication backend
    - Sessions managed by Django session framework
    - Prevents brute force attacks via rate limiting (implement at production)
    - Case-sensitive username (Django default)
    - Supports login by username or email
    """
    
    template_name = 'aline_uwamahoro/login.html'
    form_class = CustomAuthenticationForm
    
    def get(self, request, *args, **kwargs):
        """Display login form."""
        if request.user.is_authenticated:
            return redirect('aline_uwamahoro:dashboard')
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        """Process login form submission."""
        form = self.form_class(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page or dashboard
            next_url = request.GET.get('next', reverse_lazy('aline_uwamahoro:dashboard'))
            return redirect(next_url)
        
        messages.error(request, 'Invalid username/email or password.')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """
    User logout view.
    
    Terminates the user's session and clears authentication cookies.
    
    Security considerations:
    - Session is properly terminated
    - Authentication cookie is removed
    - User is redirected to home page
    """
    
    def get(self, request):
        """Handle logout."""
        if request.user.is_authenticated:
            username = request.user.username
            logout(request)
            messages.success(request, f'You have been logged out. Goodbye, {username}!')
        return redirect('aline_uwamahoro:home')


# ============================================================================
# PROTECTED VIEWS (Require Authentication)
# ============================================================================

@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """
    Authenticated user dashboard.
    
    Displays user's profile summary and quick access to account features.
    Only accessible to logged-in users.
    
    Security:
    - @login_required decorator enforces authentication
    - User can only see their own dashboard
    """
    
    template_name = 'aline_uwamahoro/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(UserProfile, user=self.request.user)
        context['total_students'] = User.objects.count()
        return context


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """
    User profile view - GET displays profile, POST updates profile.
    
    Allows authenticated users to view and update their profile information.
    
    Security:
    - @login_required enforces authentication
    - Users can only edit their own profile
    - Email uniqueness validated
    """
    
    template_name = 'aline_uwamahoro/profile.html'
    form_class = UserProfileForm
    
    def get(self, request, *args, **kwargs):
        """Display user profile."""
        profile = get_object_or_404(UserProfile, user=request.user)
        form = self.form_class(instance=profile)
        return render(request, self.template_name, {
            'profile': profile,
            'form': form,
            'edit_mode': False
        })
    
    def post(self, request, *args, **kwargs):
        """Update user profile."""
        profile = get_object_or_404(UserProfile, user=request.user)
        form = self.form_class(request.POST, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('aline_uwamahoro:profile')
        
        return render(request, self.template_name, {
            'profile': profile,
            'form': form,
            'edit_mode': True
        })


@method_decorator(login_required, name='dispatch')
class PasswordChangeView(View):
    """
    Password change view.
    
    Allows authenticated users to change their password securely.
    
    Security:
    - @login_required enforces authentication
    - Requires current password verification
    - Uses Django's password validation
    - Hashed with Django's default PBKDF2 algorithm
    """
    
    template_name = 'aline_uwamahoro/password_change.html'
    form_class = CustomPasswordChangeForm
    
    def get(self, request, *args, **kwargs):
        """Display password change form."""
        form = self.form_class(user=request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        """Process password change."""
        form = self.form_class(user=request.user, data=request.POST)
        
        if form.is_valid():
            user = form.save()
            # Update session to prevent logout after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('aline_uwamahoro:profile')
        
        return render(request, self.template_name, {'form': form})

