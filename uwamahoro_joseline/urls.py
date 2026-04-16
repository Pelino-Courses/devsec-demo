from django.urls import path
from . import views

app_name = "uwamahoro_joseline"

urlpatterns = [
    # Public/Unauthenticated views
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    
    # Password reset views (public)
    path("password-reset/", views.SecurePasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.SecurePasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.SecurePasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/complete/", views.SecurePasswordResetCompleteView.as_view(), name="password_reset_complete"),
    
    # Student views (authenticated)
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("user/<int:user_id>/", views.view_user_profile, name="view_user_profile"),
    path("user/<int:user_id>/edit/", views.edit_user_account, name="edit_user_account"),
    path("password-change/", views.password_change_view, name="password_change"),
    path("password-change/done/", views.password_change_done_view, name="password_change_done"),
    
    # Instructor views (requires instructor role)
    path("instructor/", views.instructor_panel_view, name="instructor_panel"),
    path("instructor/promote/<int:user_id>/", views.promote_user_view, name="promote_user"),
]
