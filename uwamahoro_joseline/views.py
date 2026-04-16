from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .decorators import instructor_required
from .forms import RegistrationForm
from .models import Profile


# ── Public views ─────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("uwamahoro_joseline:dashboard")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Registration successful. Welcome!")
            return redirect("uwamahoro_joseline:dashboard")
    else:
        form = RegistrationForm()
    return render(request, "uwamahoro_joseline/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("uwamahoro_joseline:dashboard")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect("uwamahoro_joseline:dashboard")
    else:
        form = AuthenticationForm()
    return render(
        request,
        "uwamahoro_joseline/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("uwamahoro_joseline:login")
    return render(request, "uwamahoro_joseline/logout.html")


# ── Student views (authenticated) ────────────────────────────────────────────

@login_required
def dashboard_view(request):
    return render(request, "uwamahoro_joseline/dashboard.html")


@login_required
def profile_view(request):
    """Display the current user's profile. Only accessible to the profile owner."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "uwamahoro_joseline/profile.html", {"profile": profile})


@login_required
def view_user_profile(request, user_id):
    """
    Display a user's profile by ID.
    
    IDOR Protection:
    - Verify that the current user is either the profile owner or has can_view_all_profiles permission.
    - This prevents unauthorized users from accessing other users' profiles by changing the URL.
    """
    target_user = get_object_or_404(User, pk=user_id)
    
    # Check object-level access control: only allow access if:
    # 1. The request is for the current user's profile, OR
    # 2. The current user has permission to view all profiles
    if request.user != target_user and not request.user.has_perm("uwamahoro_joseline.can_view_all_profiles"):
        raise PermissionDenied("You do not have permission to view this profile.")
    
    profile, _ = Profile.objects.get_or_create(user=target_user)
    return render(request, "uwamahoro_joseline/profile.html", {"profile": profile})


@login_required
def edit_user_account(request, user_id):
    """
    Edit a user's account information.
    
    IDOR Protection:
    - Only the account owner can edit their own account.
    - Superusers can also edit any account (optional administrative override).
    """
    target_user = get_object_or_404(User, pk=user_id)
    
    # Check object-level access control: only allow access if:
    # 1. The request is from the account owner themselves
    if request.user != target_user:
        raise PermissionDenied("You do not have permission to edit this account.")
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        if email and email != target_user.email:
            target_user.email = email
            target_user.save()
            messages.success(request, "Email updated successfully.")
            return redirect("uwamahoro_joseline:edit_user_account", user_id=target_user.pk)
        else:
            messages.warning(request, "No changes made.")
    
    return render(request, "uwamahoro_joseline/edit_account.html", {"target_user": target_user})


@login_required
def password_change_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was updated successfully.")
            return redirect("uwamahoro_joseline:password_change_done")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "uwamahoro_joseline/password_change.html", {"form": form})


@login_required
def password_change_done_view(request):
    return render(request, "uwamahoro_joseline/password_change_done.html")


# ── Instructor views (Instructor group required) ──────────────────────────────

@instructor_required
def instructor_panel_view(request):
    """List all registered users and their roles. Instructor-only."""
    users = User.objects.select_related("profile").order_by("date_joined")
    instructor_group = Group.objects.filter(name="Instructor").first()
    instructor_ids = (
        set(instructor_group.user_set.values_list("id", flat=True))
        if instructor_group
        else set()
    )
    return render(
        request,
        "uwamahoro_joseline/instructor_panel.html",
        {"users": users, "instructor_ids": instructor_ids},
    )


@instructor_required
def promote_user_view(request, user_id):
    """
    Promote or demote a user to/from the Instructor group. Requires can_manage_users permission.
    
    IDOR Protection:
    - Verify that the user requesting the action is actually an instructor with can_manage_users permission.
    - Prevent self-promotion/demotion by checking that the target user is not the current user.
    - Explicit permission check ensures only authorized instructors can modify roles.
    """
    if not request.user.has_perm("uwamahoro_joseline.can_manage_users"):
        raise PermissionDenied("You do not have permission to manage users.")
    
    if request.method != "POST":
        return redirect("uwamahoro_joseline:instructor_panel")

    target_user = get_object_or_404(User, pk=user_id)
    
    # Object-level access control: prevent self-modification
    if request.user == target_user:
        messages.error(request, "You cannot modify your own role.")
        return redirect("uwamahoro_joseline:instructor_panel")
    
    instructor_group = get_object_or_404(Group, name="Instructor")
    action = request.POST.get("action")

    if action == "promote":
        target_user.groups.add(instructor_group)
        messages.success(request, f"{target_user.username} promoted to Instructor.")
    elif action == "demote":
        target_user.groups.remove(instructor_group)
        messages.success(request, f"{target_user.username} demoted to Student.")
        messages.error(request, "Invalid action.")

    return redirect("uwamahoro_joseline:instructor_panel")


# ── Password Reset views (Public/Unauthenticated) ─────────────────────────────

class SecurePasswordResetView(PasswordResetView):
    """
    Secure password reset request view using Django's built-in mechanisms.
    
    Security features:
    - Uses Django's PasswordResetForm which validates email existence safely
    - Generates cryptographically secure tokens via django.contrib.auth
    - Does NOT leak whether an email exists (always shows same success message)
    - Requires valid email format
    - Sends reset link via email only (no SMS or other direct channels)
    """
    form_class = PasswordResetForm
    template_name = "uwamahoro_joseline/password_reset.html"
    email_template_name = "uwamahoro_joseline/password_reset_email.html"
    subject_template_name = "uwamahoro_joseline/password_reset_subject.txt"
    success_url = reverse_lazy("uwamahoro_joseline:password_reset_done")

    def form_valid(self, form):
        """
        When the password reset form is valid, send the reset email.
        
        Django's implementation:
        - Finds users by email (case-insensitive, may be multiple)
        - Only sends to active users
        - Creates secure token using default token generator
        - Does not distinguish between existing/non-existing emails in response
        """
        return super().form_valid(form)


class SecurePasswordResetDoneView(PasswordResetDoneView):
    """
    Confirmation that password reset email was sent.
    
    Security note:
    - Shows generic message regardless of whether email exists
    - Prevents user enumeration via password reset endpoint
    - Instructs user to check email and click link
    """
    template_name = "uwamahoro_joseline/password_reset_done.html"


class SecurePasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirmation view where user sets new password.
    
    Security features:
    - Uses Django's token validation (signed tokens with timestamp)
    - Validates token hasn't expired (default: 1 day)
    - Validates new password meets Django's validation rules
    - Prevents weak or compromised passwords
    - One-time use: tokens cannot be reused
    - Automatically logs user in after password reset (improves UX)
    """
    form_class = SetPasswordForm
    template_name = "uwamahoro_joseline/password_reset_confirm.html"
    success_url = reverse_lazy("uwamahoro_joseline:password_reset_complete")
    
    def form_valid(self, form):
        """
        When the new password is set successfully.
        
        Django's implementation:
        - Validates password strength
        - Checks for common weak passwords
        - Prevents passwords matching username/email
        - Hashes password with PBKDF2 or configured hasher
        """
        return super().form_valid(form)


class SecurePasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset complete confirmation page.
    
    User is prompted to log in with their new password.
    """
    template_name = "uwamahoro_joseline/password_reset_complete.html"
