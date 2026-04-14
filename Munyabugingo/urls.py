from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'Munyabugingo'

urlpatterns = [
    # Registration
    path('register/', views.register, name='register'),
    
    # Login/Logout
    path('login/', auth_views.LoginView.as_view(template_name='olivier/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard (protected)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Password change
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='olivier/password_change.html',
        success_url='/password-change-done/'
    ), name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='olivier/password_change_done.html'
    ), name='password_change_done'),
    
    # Profile view
    path('profile/', views.profile, name='profile'),
    path('profile/<int:pk>/', views.profile_detail, name='profile_detail'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]