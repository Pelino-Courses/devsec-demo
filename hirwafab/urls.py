from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'hirwafab'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Student/Authenticated User URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('users/', views.user_directory, name='user_directory'),

    # Instructor/Staff URLs
    path('users/directory/', views.user_directory_full, name='user_directory_full'),
    path('users/<int:user_id>/', views.view_user_profile, name='view_user_profile'),
    path('activity/', views.user_activity, name='user_activity'),
    path('reports/', views.reports, name='reports'),

    # Password reset (Django built-in views, custom templates)
    path('password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='hirwafab/password_reset.html',
            email_template_name='hirwafab/password_reset_email.txt',
            subject_template_name='hirwafab/password_reset_subject.txt',
            success_url=reverse_lazy('hirwafab:password_reset_done'),
        ),
        name='password_reset',
    ),
    path('password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='hirwafab/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path('password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='hirwafab/password_reset_confirm.html',
            success_url=reverse_lazy('hirwafab:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path('password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='hirwafab/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
