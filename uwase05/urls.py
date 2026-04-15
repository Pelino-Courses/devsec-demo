from django.urls import path

from .views import (
    HomeView,
    RegisterView,
    UserLoginView,
    UserLogoutView,
    dashboard,
    profile,
    UserPasswordChangeView,
    PasswordChangeDoneView,
    UserPasswordResetView,
    UserPasswordResetDoneView,
    UserPasswordResetConfirmView,
    UserPasswordResetCompleteView,
    InstructorDashboardView,
)

app_name = 'uwase05'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
    path('password/change/', UserPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password/reset/', UserPasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', UserPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', UserPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', UserPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('instructor/', InstructorDashboardView.as_view(), name='instructor_dashboard'),
]
