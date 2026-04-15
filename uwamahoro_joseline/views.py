from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegistrationForm
from .models import Profile


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
