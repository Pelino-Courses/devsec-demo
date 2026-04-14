"""
URL configuration for aline_uwamahoro authentication app.

This module defines all authentication-related URL patterns including:
- Registration, login, logout
- Protected profile and dashboard pages
- Password change functionality
"""

from django.urls import path
from . import views

app_name = 'aline_uwamahoro'  # Namespace for reverse URL lookups

urlpatterns = [
    # Public pages
    path('', views.HomeView.as_view(), name='home'),
    
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Protected endpoints (require login)
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('change-password/', views.PasswordChangeView.as_view(), name='password_change'),
]
