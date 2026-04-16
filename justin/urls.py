from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    register_view, login_view, logout_view, profile_view,
    change_password, update_profile_view, home_view,
    admin_dashboard, user_management, change_user_role, view_all_profiles,
    view_user_profile
)

urlpatterns = [
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', update_profile_view, name='update_profile'),
    path('profile/<int:user_id>/', view_user_profile, name='view_user_profile'),
    path('password-change/', change_password, name='password_change'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('users/', user_management, name='user_management'),
    path('users/<int:user_id>/role/', change_user_role, name='change_user_role'),
    path('all-profiles/', view_all_profiles, name='all_profiles'),
]