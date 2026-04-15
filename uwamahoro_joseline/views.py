from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "uwamahoro_joseline/profile.html", {"profile": profile})


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
    """Promote or demote a user to/from the Instructor group. Requires can_manage_users."""
    if not request.user.has_perm("uwamahoro_joseline.can_manage_users"):
        raise PermissionDenied
    if request.method != "POST":
        return redirect("uwamahoro_joseline:instructor_panel")

    target_user = get_object_or_404(User, pk=user_id)
    instructor_group = get_object_or_404(Group, name="Instructor")
    action = request.POST.get("action")

    if action == "promote":
        target_user.groups.add(instructor_group)
        messages.success(request, f"{target_user.username} promoted to Instructor.")
    elif action == "demote":
        target_user.groups.remove(instructor_group)
        messages.success(request, f"{target_user.username} demoted to Student.")
    else:
        messages.error(request, "Invalid action.")

    return redirect("uwamahoro_joseline:instructor_panel")
