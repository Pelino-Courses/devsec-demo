from django.urls import path

from .views import (
    AccountView,
    HomeView,
    PrivilegedDashboardView,
    RegisterView,
    UserLoginView,
    UserLogoutView,
    UserPasswordChangeDoneView,
    UserPasswordChangeView,
)

app_name = "igihozo"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("account/", AccountView.as_view(), name="account"),
    path("privileged-dashboard/", PrivilegedDashboardView.as_view(), name="privileged_dashboard"),
    path("password-change/", UserPasswordChangeView.as_view(), name="password_change"),
    path(
        "password-change/done/",
        UserPasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
]
