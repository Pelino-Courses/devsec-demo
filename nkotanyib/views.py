from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User

def is_privileged(user):
    """Check if a user is an instructor or staff."""
    return user.is_authenticated and (user.is_staff or user.groups.filter(name='Instructor').exists())

def register(request):
    if request.user.is_authenticated:
        return redirect('profile')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful. Welcome!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
        
    return render(request, 'nkotanyib/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'nkotanyib/profile.html', {
        'user': request.user
    })

@login_required
def privileged_dashboard(request):
    if not is_privileged(request.user):
        messages.error(request, 'You do not have permission to access the privileged dashboard.')
        return redirect('profile')
    return render(request, 'nkotanyib/privileged_dashboard.html', {
        'user': request.user
    })

@login_required
def edit_profile(request, user_id):
    # IDOR Prevention: Ensure that users can only open and modify their own accounts
    if request.user.id != user_id:
        messages.error(request, 'You do not have permission to access or edit this profile.')
        return redirect('profile')

    user_to_edit = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            user_to_edit.email = email
            user_to_edit.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

    return render(request, 'nkotanyib/edit_profile.html', {
        'profile_user': user_to_edit
    })

