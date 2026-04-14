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
    
    # Admin/Instructor
    path('manage-users/', views.manage_users, name='manage_users'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('reset-password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    
    # Public
    path('user/<int:user_id>/', views.public_profile, name='public_profile'),
]
