from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'eduard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<int:user_id>/', views.profile_by_id, name='profile_by_id'),
    path('change-password/', views.change_password, name='change_password'),
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),

    # Password reset flow - all four steps use Django built-in views
    # with our own templates so the design stays consistent.
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='eduard/password_reset.html',
            email_template_name='eduard/password_reset_email.txt',
            subject_template_name='eduard/password_reset_subject.txt',
            success_url='/password-reset/sent/',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='eduard/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='eduard/password_reset_confirm.html',
            success_url='/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='eduard/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]