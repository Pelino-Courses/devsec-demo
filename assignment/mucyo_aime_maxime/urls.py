from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'mucyo_aime_maxime'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_detail_view, name='profile_detail'),
    path('password-change/', views.password_change_view, name='password_change'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='mucyo_aime_maxime/password_reset_form.html',
             email_template_name='mucyo_aime_maxime/password_reset_email.html',
             success_url='/auth/password-reset/done/'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='mucyo_aime_maxime/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='mucyo_aime_maxime/password_reset_confirm.html',
             success_url='/auth/password-reset-complete/'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='mucyo_aime_maxime/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Staff-only routes
    path('staff/dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
    
    # Instructor-only routes
    path('instructor/reports/', views.instructor_reports_view, name='instructor_reports'),
]
