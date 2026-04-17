import mimetypes
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.http import Http404, FileResponse
from django.contrib.auth.models import User
from .forms import BioForm, AvatarUploadForm, DocumentUploadForm
import logging

logger = logging.getLogger('security')


def home(request):
    return render(request, 'shema/home.html')


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            ip = request.META.get('REMOTE_ADDR')
            logger.info(f"NEW_USER_REGISTERED: '{user.username}' from IP {ip}")
            messages.success(request, f"Account created successfully for {user.username}!")
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'shema/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}.")

                next_url = request.GET.get('next', 'home')
                if not url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    next_url = 'home'
                return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'shema/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('home')


@login_required
def profile_view(request, username):
    if request.user.username != username:
        raise Http404("Profile not found")
    profile_user = get_object_or_404(User, username=username)
    return render(request, 'shema/profile.html', {'profile_user': profile_user})


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile', username=request.user.username)
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'shema/password_change.html', {'form': form})


@login_required
@permission_required('shema.view_instructor_dashboard', raise_exception=True)
def instructor_dashboard_view(request):
    return render(request, 'shema/instructor_dashboard.html')


@login_required
def update_profile_view(request, username):
    if request.user.username != username:
        raise Http404("Profile not found")
    profile_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        form = BioForm(request.POST, instance=profile_user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile', username=username)
    return redirect('profile', username=username)


@login_required
def upload_avatar_view(request, username):
    if request.user.username != username:
        raise Http404("Profile not found")
    profile_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile_user.profile)
        if form.is_valid():
            form.save()
            logger.info(f"AVATAR_UPLOADED: '{username}' uploaded a new avatar")
            messages.success(request, "Avatar updated successfully!")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    return redirect('profile', username=username)


@login_required
def upload_document_view(request, username):
    if request.user.username != username:
        raise Http404("Profile not found")
    profile_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES, instance=profile_user.profile)
        if form.is_valid():
            form.save()
            logger.info(f"DOCUMENT_UPLOADED: '{username}' uploaded a document")
            messages.success(request, "Document uploaded successfully!")
        else:
            for error in form.errors.values():
                messages.error(request, error)
    return redirect('profile', username=username)


@login_required
def serve_upload_view(request, username, filetype):
    """Serve private uploads only to the file owner."""
    if request.user.username != username:
        raise Http404("Not found")
    profile_user = get_object_or_404(User, username=username)
    profile = profile_user.profile

    if filetype == 'avatar' and profile.avatar:
        f = profile.avatar
    elif filetype == 'document' and profile.document:
        f = profile.document
    else:
        raise Http404("Not found")

    ext = os.path.splitext(f.name)[1].lower()
    content_type = mimetypes.types_map.get(ext, 'application/octet-stream')
    return FileResponse(f.open('rb'), content_type=content_type)
