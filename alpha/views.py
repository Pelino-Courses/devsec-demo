from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .forms import CustomUserCreationForm
from .models import UserProfile

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'alpha/register.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'alpha/profile.html')

@login_required
def protected_view(request):
    return render(request, 'alpha/protected.html')

@login_required
@permission_required('alpha.can_view_dashboard', raise_exception=True)
def instructor_dashboard(request):
    return render(request, 'alpha/dashboard.html')
