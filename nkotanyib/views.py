from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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
