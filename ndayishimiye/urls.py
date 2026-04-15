from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'ndayishimiye'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/<int:user_id>/', views.profile_by_id, name='profile_by_id'),
    path('password-change/', views.password_change, name='password_change'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),

    # Password reset URLs using Django built-ins
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='ndayishimiye/password_reset.html',
            email_template_name='ndayishimiye/password_reset_email.html',
            subject_template_name='ndayishimiye/password_reset_subject.txt',
            success_url='/ndayishimiye/password-reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='ndayishimiye/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='ndayishimiye/password_reset_confirm.html',
            success_url='/ndayishimiye/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='ndayishimiye/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
