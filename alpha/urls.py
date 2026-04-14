from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.RateLimitedLoginView.as_view(template_name='alpha/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='alpha/logged_out.html'), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='alpha/password_change_form.html', success_url='/alpha/password-change/done/'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='alpha/password_change_done.html'), name='password_change_done'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='alpha/password_reset_form.html', success_url='/alpha/password-reset/done/'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='alpha/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='alpha/password_reset_confirm.html', success_url='/alpha/reset/done/'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='alpha/password_reset_complete.html'), name='password_reset_complete'),

    path('profile/', views.profile, name='profile'),
    path('profile/<int:user_id>/update/', views.update_profile, name='update_profile'),
    path('protected/', views.protected_view, name='protected_view'),
    path('instructor-dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
]
