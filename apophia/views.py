import os

from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
)
from django.http import FileResponse, Http404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import timedelta

from .models import LoginAttempt, Document
from .forms import ApophiaUserCreationForm, UserUpdateForm, ProfileUpdateForm, DocumentUploadForm
from . import audit

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = ApophiaUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            audit.log_registration(request, user.username)
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
    else:
        form = ApophiaUserCreationForm()
    return render(request, 'apophia/register.html', {'form': form})

@login_required
def profile(request, username=None):
    # Determine target user: either current user or one specified in URL
    if username:
        target_user = get_object_or_404(User, username=username)
    else:
        target_user = request.user

    # RBAC/IDOR Check: Only self or staff can access
    if target_user != request.user and not request.user.is_staff:
        raise PermissionDenied("You do not have permission to access another user's profile.")

    if request.method == 'POST':
        # Safety Check: Even staff cannot modify another's credentials/details here
        if target_user != request.user:
            raise PermissionDenied("You cannot modify another user's profile information.")

        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=target_user)
        p_form = ProfileUpdateForm(instance=target_user.profile)

    documents = []
    document_form = None
    if target_user == request.user:
        documents = Document.objects.filter(user=request.user)
        document_form = DocumentUploadForm()

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'target_user': target_user,
        'documents': documents,
        'document_form': document_form,
    }
    return render(request, 'apophia/profile.html', context)

class ApophiaLoginView(LoginView):
    template_name = 'apophia/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = (
            self.request.POST.get(self.redirect_field_name)
            or self.request.GET.get(self.redirect_field_name, '')
        )
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        ):
            return next_url
        return self.get_default_redirect_url()

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username', '')
        ip_address = self.get_client_ip()

        # Check for lockout (5 failures in the last 15 minutes)
        fifteen_mins_ago = timezone.now() - timedelta(minutes=15)
        failures = LoginAttempt.objects.filter(
            username=username,
            ip_address=ip_address,
            timestamp__gte=fifteen_mins_ago
        ).count()

        if failures >= 5:
            audit.log_login_lockout(request, username)
            messages.error(request, 'Too many failed login attempts. Your account is temporarily locked. Please try again in 15 minutes.')
            return render(request, self.template_name, self.get_context_data())

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        audit.log_login_success(self.request, form.get_user().username)
        return response

    def form_invalid(self, form):
        username = self.request.POST.get('username', '')
        ip_address = self.get_client_ip()
        LoginAttempt.objects.create(username=username, ip_address=ip_address)
        audit.log_login_failure(self.request, username)
        return super().form_invalid(form)

class ApophiaLogoutView(LogoutView):
    template_name = 'apophia/logout.html'

    def post(self, request, *args, **kwargs):
        username = request.user.username if request.user.is_authenticated else ''
        response = super().post(request, *args, **kwargs)
        if username:
            audit.log_logout(request, username)
        return response

class ApophiaPasswordChangeView(PasswordChangeView):
    template_name = 'apophia/password_change.html'
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        audit.log_password_change(self.request, self.request.user.username)
        return response

class ApophiaPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'apophia/password_change_done.html'

@login_required
def dashboard(request):
    return render(request, 'apophia/dashboard.html')

@user_passes_test(lambda u: u.is_staff)
def staff_directory(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'apophia/staff_directory.html', {'users': users})

class ApophiaPasswordResetView(PasswordResetView):
    template_name = 'apophia/password_reset_form.html'
    email_template_name = 'apophia/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data.get('email', '')
        response = super().form_valid(form)
        audit.log_password_reset_requested(self.request, email)
        return response

class ApophiaPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'apophia/password_reset_done.html'

class ApophiaPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'apophia/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.user:
            audit.log_password_reset_complete(self.request, self.user.username)
        return response

class ApophiaPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'apophia/password_reset_complete.html'


# ------------------------------------------------------------------ #
# Document upload / download / delete
# ------------------------------------------------------------------ #

@login_required
def document_upload(request):
    if request.method != 'POST':
        return redirect('profile')

    form = DocumentUploadForm(request.POST, request.FILES)
    if form.is_valid():
        upload = request.FILES['file']
        doc = form.save(commit=False)
        doc.user = request.user
        # Sanitise the original filename: strip path components and null bytes,
        # then cap at the field's max_length so the DB write never fails.
        doc.original_filename = os.path.basename(
            upload.name.replace('\x00', '')
        )[:255]
        doc.file_size = upload.size
        doc.save()
        messages.success(request, f'"{doc.original_filename}" uploaded successfully.')
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect('profile')


@login_required
def document_download(request, pk):
    # The user= filter is the IDOR guard: a user can only download their own files.
    doc = get_object_or_404(Document, pk=pk, user=request.user)
    try:
        file_handle = doc.file.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404("The requested file could not be found.")

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=doc.original_filename,
    )
    # Force download and prevent MIME sniffing even for unexpected content.
    response['Content-Type'] = 'application/octet-stream'
    response['X-Content-Type-Options'] = 'nosniff'
    # Tight CSP on the download response so browsers won't execute anything.
    response['Content-Security-Policy'] = "default-src 'none'"
    return response


@login_required
def document_delete(request, pk):
    if request.method == 'POST':
        doc = get_object_or_404(Document, pk=pk, user=request.user)
        name = doc.original_filename
        doc.delete()  # post_delete signal removes the physical file
        messages.success(request, f'"{name}" deleted.')
    return redirect('profile')
