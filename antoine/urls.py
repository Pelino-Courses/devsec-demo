from django.urls import path
from . import views

app_name = 'antoine'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard & Profile
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # History
    path('login-history/', views.login_history, name='login_history'),
    
    # Public
    path('user/<int:user_id>/', views.public_profile, name='public_profile'),
]
