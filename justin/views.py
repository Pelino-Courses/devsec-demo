from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.http import FileResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Profile, Document, Role
from .forms import RegisterForm, ProfileForm, DocumentUploadForm


def index(request):
    """Home page."""
    return render(request, 'justin/index.html')


def register(request):
    """User registration."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create profile for new user
            Profile.objects.create(user=user, role=Role.USER)
            # Assign to standard group
            standard_group, _ = Group.objects.get_or_create(name='Standard')
            user.groups.add(standard_group)
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'justin/register.html', {'form': form})


@login_required
def profile(request):
    """User profile with secure file upload handling."""
    profile = get_object_or_404(Profile, user=request.user)
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile')
            except ValidationError as e:
                messages.error(request, f'Error updating profile: {e.message}')
    else:
        form = ProfileForm(instance=profile)
    
    documents = Document.objects.filter(user=request.user)
    
    context = {
        'profile': profile,
        'form': form,
        'documents': documents,
    }
    return render(request, 'justin/profile.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def upload_document(request):
    """Secure document upload with validation."""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                document = form.save(commit=False)
                document.user = request.user
                document.full_clean()  # Validate including file validators
                document.save()
                messages.success(request, 'Document uploaded successfully!')
                return redirect('profile')
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
                else:
                    messages.error(request, f'Upload error: {e.message if hasattr(e, "message") else str(e)}')
    else:
        form = DocumentUploadForm()
    
    return render(request, 'justin/upload_document.html', {'form': form})


@login_required
def download_document(request, doc_id):
    """Secure document download with access control.
    
    Access is restricted to:
    - Document owner
    - Staff/Admin users
    """
    document = get_object_or_404(Document, id=doc_id)
    
    # Access control check
    is_owner = document.user == request.user
    is_staff = request.user.is_staff or request.user.groups.filter(name='Privileged').exists()
    
    if not (is_owner or is_staff):
        return HttpResponseForbidden('You do not have permission to download this document.')
    
    try:
        response = FileResponse(document.file.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
        return response
    except Exception as e:
        messages.error(request, 'Error downloading file.')
        return redirect('profile')


@login_required
def delete_document(request, doc_id):
    """Delete document (owner or admin only)."""
    document = get_object_or_404(Document, id=doc_id)
    
    # Access control: only owner or admin can delete
    if document.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden('You do not have permission to delete this document.')
    
    if request.method == 'POST':
        document.file.delete(save=False)
        document.delete()
        messages.success(request, 'Document deleted successfully.')
        return redirect('profile')
    
    return render(request, 'justin/confirm_delete_document.html', {'document': document})


def all_profiles(request):
    """View all user profiles (staff/admin only for now)."""
    if not (request.user.is_staff or request.user.groups.filter(name='Privileged').exists()):
        return HttpResponseForbidden('You do not have permission to view all profiles.')
    
    profiles = Profile.objects.all()
    # Only show public documents
    context = {
        'profiles': profiles,
    }
    return render(request, 'justin/all_profiles.html', context)


@login_required
def change_user_role(request, user_id):
    """Change user role (admin only)."""
    if not request.user.is_staff:
        return HttpResponseForbidden('Only administrators can change user roles.')
    
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(Profile, user=user)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in [choice[0] for choice in Role.choices]:
            profile.role = new_role
            profile.save()
            messages.success(request, f'{user.username} role changed to {new_role}.')
            return redirect('all_profiles')
    
    context = {
        'target_user': user,
        'profile': profile,
        'roles': Role.choices,
    }
    return render(request, 'justin/change_user_role.html', context)


def login_view(request):
    """Login page (uses Django's auth backend)."""
    return render(request, 'justin/login.html')


@login_required
def change_password(request):
    """Change password page."""
    return render(request, 'justin/change_password.html')
