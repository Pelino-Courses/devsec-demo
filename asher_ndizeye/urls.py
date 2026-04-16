from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'asher_ndizeye'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('dashboard/', views.dashboard, name='dashboard_explicit'),
    path('staff/', views.StaffDashboardView.as_view(), name='staff_dashboard'),

    # --- SECURE PASSWORD RESET FLOW ---
    # 1. Request link
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='asher_ndizeye/password_reset.html',
             email_template_name='asher_ndizeye/password_reset_email.html',
             subject_template_name='asher_ndizeye/password_reset_subject.txt',
             success_url='/password-reset/done/' # Adjust based on your root config
         ), 
         name='password_reset'),
         
    # 2. Request sent confirmation
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='asher_ndizeye/password_reset_done.html'
         ), 
         name='password_reset_done'),
         
    # 3. Link clicked from email (The token step)
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='asher_ndizeye/password_reset_confirm.html',
             success_url='/password-reset/complete/'
         ), 
         name='password_reset_confirm'),
         
    # 4. Success message
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='asher_ndizeye/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]