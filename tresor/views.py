from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from .decorators import instructor_required
from .forms import RegistrationForm, LoginForm, ProfileUpdateForm, AvatarUploadForm, DocumentUploadForm
from .models import LoginAttempt, Document


def _is_instructor(user):
    return user.groups.filter(name='instructor').exists() or user.is_staff


def register(request):
    if request.user.is_authenticated:
        return redirect('tresor:dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('tresor:dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'tresor/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('tresor:dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        attempt, _ = LoginAttempt.objects.get_or_create(username=username)

        if attempt.is_locked():
            messages.error(request, 'Too many failed attempts. Please try again later.')
            return render(request, 'tresor/login.html', {'form': LoginForm()})

        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            attempt.record_success()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}.')
            next_url = request.GET.get('next', 'tresor:dashboard')
            return redirect(next_url)
        else:
            attempt.record_failure()
    else:
        form = LoginForm()
    return render(request, 'tresor/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('tresor:login')
    return render(request, 'tresor/logout_confirm.html')


@login_required
def dashboard(request):
    return render(request, 'tresor/dashboard.html', {'is_instructor': _is_instructor(request.user)})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('tresor:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)
    return render(request, 'tresor/profile.html', {'form': form})


@login_required
def profile_view(request, username):
    target_user = get_object_or_404(User, username=username)

    if request.user != target_user and not _is_instructor(request.user):
        raise PermissionDenied

    return render(request, 'tresor/profile_view.html', {'target_user': target_user})


@login_required
def profile_edit(request, username):
    target_user = get_object_or_404(User, username=username)

    if request.user != target_user:
        raise PermissionDenied

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=target_user.profile, user=target_user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('tresor:profile_view', username=target_user.username)
    else:
        form = ProfileUpdateForm(instance=target_user.profile, user=target_user)
    return render(request, 'tresor/profile.html', {'form': form})


@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully.')
            return redirect('tresor:password_change_done')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'tresor/password_change.html', {'form': form})


@login_required
def password_change_done(request):
    return render(request, 'tresor/password_change_done.html')


@instructor_required
def instructor_dashboard(request):
    users = User.objects.select_related('profile').order_by('username')
    return render(request, 'tresor/instructor_dashboard.html', {'users': users})


@login_required
def avatar_upload(request):
    if request.method == 'POST':
        form = AvatarUploadForm(request.POST, request.FILES)
        if form.is_valid():
            profile = request.user.profile
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar.save(form.cleaned_data['avatar'].name, form.cleaned_data['avatar'], save=True)
            messages.success(request, 'Avatar updated.')
            return redirect('tresor:profile')
    else:
        form = AvatarUploadForm()
    return render(request, 'tresor/avatar_upload.html', {'form': form})


@login_required
def documents(request):
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['document']
            doc = Document(owner=request.user, original_name=uploaded.name)
            doc.file.save(uploaded.name, uploaded, save=True)
            messages.success(request, 'Document uploaded.')
            return redirect('tresor:documents')
    else:
        form = DocumentUploadForm()
    return render(request, 'tresor/documents.html', {
        'form': form,
        'documents': Document.objects.filter(owner=request.user).order_by('-uploaded_at'),
    })


@login_required
def document_download(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if request.user != doc.owner and not _is_instructor(request.user):
        raise PermissionDenied
    _CONTENT_TYPES = {'.pdf': 'application/pdf', '.txt': 'text/plain; charset=utf-8'}
    import os
    ext = os.path.splitext(doc.original_name)[1].lower()
    content_type = _CONTENT_TYPES.get(ext, 'application/octet-stream')
    response = FileResponse(doc.file.open('rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{doc.original_name}"'
    return response
