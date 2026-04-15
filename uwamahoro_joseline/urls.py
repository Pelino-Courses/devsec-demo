from django.urls import path

from . import views

app_name = "uwamahoro_joseline"

urlpatterns = [
    # Public
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Student (authenticated)
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("password/change/", views.password_change_view, name="password_change"),
    path("password/change/done/", views.password_change_done_view, name="password_change_done"),
    # Instructor only
    path("instructor/", views.instructor_panel_view, name="instructor_panel"),
    path("instructor/promote/<int:user_id>/", views.promote_user_view, name="promote_user"),
]
