from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, ListView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.core.cache import cache

from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    CustomPasswordChangeForm,
    UserProfileForm
)
from .models import UserProfile
from .decorators import (
    get_user_role,
    is_admin,
    is_staff_or_admin,
    is_instructor_or_above,
    admin_required,
    staff_required,
    instructor_required,
    RoleRequiredMixin
)


class HomeView(TemplateView):
    """
    Public home page view.
    
    This view displays the landing page available to all users.
    Provides role-aware content based on user authentication status.
    """
    template_name = 'aline/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_students'] = User.objects.count()
        
        # Add role information if user is authenticated
        if self.request.user.is_authenticated:
            context['user_role'] = get_user_role(self.request.user)
            context['is_admin'] = is_admin(self.request.user)
            context['is_staff'] = is_staff_or_admin(self.request.user)
            context['is_instructor'] = is_instructor_or_above(self.request.user)
        
        return context


class RegisterView(View):
    """
    User registration view.
    
    Handles GET (display form) and POST (process registration) requests.
    Creates both User and UserProfile objects atomically.
    """
    template_name = 'aline/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('aline:login')
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('aline:dashboard')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    messages.success(
                        request,
                        f'Welcome, {user.username}! Your account has been created. Please log in.'
                    )
                    return redirect(self.success_url)
            except Exception:
                messages.error(request, 'An error occurred during registration. Please try again.')
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    """
    User login view.
    
    Handles GET (display login form) and POST (authenticate user) requests.
    """
    template_name = 'aline/login.html'
    form_class = CustomAuthenticationForm
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('aline:dashboard')
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        ip_address = request.META.get('REMOTE_ADDR')
        
        # Keys for rate limiting
        user_key = f'login_attempts:user:{username}'
        ip_key = f'login_attempts:ip:{ip_address}'
        
        # Check for lockout
        user_attempts = cache.get(user_key, 0)
        ip_attempts = cache.get(ip_key, 0)
        
        MAX_ATTEMPTS = 5
        TIMEOUT = 600  # 10 minutes
        
        if user_attempts >= MAX_ATTEMPTS or ip_attempts >= MAX_ATTEMPTS:
            messages.error(request, 'Too many failed login attempts. Please try again in 10 minutes.')
            return render(request, self.template_name, {
                'form': self.form_class(),
                'lockout': True
            })

        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Reset attempts on success
            cache.delete(user_key)
            cache.delete(ip_key)
            
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next') or request.POST.get('next') or reverse_lazy('aline:dashboard')
            return redirect(next_url)
            
        # Increment attempts on failure
        cache.set(user_key, user_attempts + 1, TIMEOUT)
        cache.set(ip_key, ip_attempts + 1, TIMEOUT)
        
        messages.error(request, 'Invalid username/email or password.')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """
    User logout view.
    """
    def get(self, request):
        if request.user.is_authenticated:
            username = request.user.username
            logout(request)
            messages.success(request, f'You have been logged out. Goodbye, {username}!')
        return redirect('aline:home')


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """
    Authenticated user dashboard.
    
    Displays role-specific information based on user permissions.
    """
    template_name = 'aline/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(UserProfile, user=self.request.user)
        context['total_students'] = User.objects.count()
        
        # Add role information
        context['user_role'] = get_user_role(self.request.user)
        context['is_admin'] = is_admin(self.request.user)
        context['is_staff'] = is_staff_or_admin(self.request.user)
        context['is_instructor'] = is_instructor_or_above(self.request.user)
        
        return context


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """
    User profile view.
    """
    template_name = 'aline/profile.html'
    form_class = UserProfileForm
    
    def _get_role_context(self):
        """Helper to add role context to response."""
        return {
            'user_role': get_user_role(self.request.user),
            'is_admin': is_admin(self.request.user),
            'is_staff': is_staff_or_admin(self.request.user),
            'is_instructor': is_instructor_or_above(self.request.user),
        }

    def get(self, request, *args, **kwargs):
        profile = get_object_or_404(UserProfile, user=request.user)
        form = self.form_class(instance=profile)
        context = {
            'profile': profile,
            'form': form,
            'edit_mode': False
        }
        context.update(self._get_role_context())
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(UserProfile, user=request.user)
        form = self.form_class(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('aline:profile')
        context = {
            'profile': profile,
            'form': form,
            'edit_mode': True
        }
        context.update(self._get_role_context())
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class PasswordChangeView(View):
    """
    Password change view.
    """
    template_name = 'aline/password_change.html'
    form_class = CustomPasswordChangeForm
    
    def _get_role_context(self):
        """Helper to add role context to response."""
        return {
            'user_role': get_user_role(self.request.user),
            'is_admin': is_admin(self.request.user),
            'is_staff': is_staff_or_admin(self.request.user),
            'is_instructor': is_instructor_or_above(self.request.user),
        }
    
    def get(self, request, *args, **kwargs):
        form = self.form_class(user=request.user)
        context = {'form': form}
        context.update(self._get_role_context())
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        form = self.form_class(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('aline:profile')
        context = {'form': form}
        context.update(self._get_role_context())
        return render(request, self.template_name, context)


# ============================================================================
# STAFF AND ADMIN VIEWS (Require appropriate permissions)
# ============================================================================

@method_decorator(staff_required, name='dispatch')
class UserManagementView(ListView):
    """
    Staff-only view for managing users and their profiles.
    
    Only staff, admins, and instructors can access this view.
    Displays a paginated list of all users with their roles.
    """
    model = User
    template_name = 'aline/admin/user_management.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        """Get all users ordered by creation date."""
        return User.objects.select_related('profile').order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = get_user_role(self.request.user)
        context['is_admin'] = is_admin(self.request.user)
        context['is_staff'] = is_staff_or_admin(self.request.user)
        context['is_instructor'] = is_instructor_or_above(self.request.user)
        context['total_users'] = User.objects.count()
        context['total_profiles'] = UserProfile.objects.count()
        
        # Add group information for each user
        for user in context['users']:
            user.assigned_groups = user.groups.values_list('name', flat=True)
        
        return context


@method_decorator(staff_required, name='dispatch')
class UserDetailView(View):
    """
    Staff-only view for viewing and managing individual user details.
    
    Allows staff/admin to view and modify user information.
    """
    template_name = 'aline/admin/user_detail.html'
    
    def get(self, request, user_id, *args, **kwargs):
        """Display user details."""
        user = get_object_or_404(User, pk=user_id)
        profile = get_object_or_404(UserProfile, user=user)
        user_groups = user.groups.all()
        
        # IDOR/Object-level check: Staff can view everyone, 
        # but we add explicit logging or restrictions if needed.
        # For now, we allow staff to view, but we'll restrict modification.
        
        return render(request, self.template_name, {
            'user': user,
            'profile': profile,
            'user_groups': user_groups,
            'all_groups': Group.objects.all(),
            'user_role': get_user_role(request.user),
            'is_admin': is_admin(request.user),
            'is_staff': is_staff_or_admin(request.user),
            'is_instructor': is_instructor_or_above(request.user),
        })
    
    def post(self, request, user_id, *args, **kwargs):
        """Update user groups and basic info."""
        target_user = get_object_or_404(User, pk=user_id)
        
        # IDOR/Privilege Escalation Protection:
        # 1. Non-admins cannot modify Admin users
        # 2. Non-admins cannot assign anyone to the Admin or Staff groups
        
        current_user_is_admin = is_admin(request.user)
        target_user_is_admin = is_admin(target_user)
        
        if not current_user_is_admin:
            if target_user_is_admin:
                messages.error(request, 'You do not have permission to modify an administrator account.')
                return HttpResponseForbidden('Permission Denied')
            
            # Check if attempting to add to privileged groups
            group_ids = request.POST.getlist('groups')
            privileged_groups = Group.objects.filter(name__in=['Admin', 'Staff'])
            privileged_group_ids = [str(g.id) for g in privileged_groups]
            
            for g_id in group_ids:
                if g_id in privileged_group_ids:
                    messages.error(request, 'You do not have permission to assign privileged roles.')
                    return HttpResponseForbidden('Permission Denied')
        
        # Get group IDs from POST data
        group_ids = request.POST.getlist('groups')
        
        # Only staff/admin can modify staff/superuser status
        if current_user_is_admin:
            target_user.is_staff = request.POST.get('is_staff') == 'on'
            target_user.is_superuser = request.POST.get('is_superuser') == 'on'
        
        # Update user groups
        target_user.groups.set(Group.objects.filter(id__in=group_ids))
        target_user.save()
        
        messages.success(request, f'Updated user {target_user.username} successfully.')
        return redirect('aline:user_detail', user_id=target_user.id)


@method_decorator(admin_required, name='dispatch')
class AdminDashboardView(TemplateView):
    """
    Admin-only dashboard with system statistics and management tools.
    
    Only superusers and admin users can access this view.
    """
    template_name = 'aline/admin/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['user_role'] = get_user_role(self.request.user)
        context['is_admin'] = is_admin(self.request.user)
        context['is_staff'] = is_staff_or_admin(self.request.user)
        context['is_instructor'] = is_instructor_or_above(self.request.user)
        
        context['total_users'] = User.objects.count()
        context['total_profiles'] = UserProfile.objects.count()
        context['total_groups'] = Group.objects.count()
        
        # User breakdown by group
        context['students'] = User.objects.filter(groups__name='Student').count()
        context['instructors'] = User.objects.filter(groups__name='Instructor').count()
        context['staff'] = User.objects.filter(groups__name='Staff').count()
        context['admins'] = User.objects.filter(groups__name='Admin').count()
        
        # Recent users
        context['recent_users'] = User.objects.order_by('-date_joined')[:10]
        
        return context


@method_decorator(instructor_required, name='dispatch')
class StudentListView(ListView):
    """
    Instructor-accessible view showing all students.
    
    Instructors can view all student profiles.
    """
    model = User
    template_name = 'aline/instructor/student_list.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        """Get all users who are students."""
        return User.objects.filter(
            groups__name='Student'
        ).select_related('profile').order_by('username')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_role'] = get_user_role(self.request.user)
        context['is_admin'] = is_admin(self.request.user)
        context['is_staff'] = is_staff_or_admin(self.request.user)
        context['is_instructor'] = is_instructor_or_above(self.request.user)
        context['total_students'] = User.objects.filter(groups__name='Student').count()
        return context
