from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created! Please login.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('profile')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})

@login_required
def upload_files(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        avatar = request.FILES.get('avatar')
        document = request.FILES.get('document')
        
        # We'll use a manual validation check here to show explicit handling,
        # but the model validators also run during .save() in a ModelForm.
        # Here we manually update fields.
        try:
            if avatar:
                profile.avatar = avatar
            if document:
                profile.document = document
            
            # This triggers full model validation including our secure validators
            profile.full_clean() 
            profile.save()
            messages.success(request, 'Files uploaded successfully!')
            return redirect('profile')
        except Exception as e:
            # Catching ValidationError from our custom validators
            messages.error(request, f'Upload failed: {str(e)}')
            
    return render(request, 'accounts/upload.html', {'profile': profile})
