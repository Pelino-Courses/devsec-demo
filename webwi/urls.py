from django.urls import path

from .views import (
    DashboardView,
    ProfileView,
    UserDirectoryView,
    UserLoginView,
    UserLogoutView,
    UserPasswordChangeDoneView,
    UserPasswordChangeView,
    UserRegistrationView,
    home_redirect,
)

app_name = 'webwi'

urlpatterns = [
    path('', home_redirect, name='home'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('users/', UserDirectoryView.as_view(), name='user_directory'),
    path('password/change/', UserPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', UserPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
