from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from .models import UserProfile

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            messages.success(request, 'Registration successful. Please login.')
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
            user = form.save()
            login(request, user)
            return redirect('profile')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.method == 'POST':
        logout(request)
    return redirect('login')

@login_required
@ensure_csrf_cookie
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile})

# FIXING CSRF MISUSE
# FIXED: Removed @csrf_exempt decorator to restore standard CSRF protection.
# Originally, this view might have been incorrectly decorated to "fix" AJAX errors.
@login_required
def update_display_name(request):
    """
    Update the user's display name via AJAX.
    This was previously misconfigured to bypass CSRF, but now properly
    requires a CSRF token in the X-CSRFToken header.
    """
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '')
        profile = request.user.userprofile
        profile.display_name = display_name
        profile.save()
        return JsonResponse({'status': 'success', 'display_name': display_name})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
