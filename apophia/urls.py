from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.ApophiaLoginView.as_view(), name='login'),
    path('logout/', views.ApophiaLogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile, name='profile_detail'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('password-change/', views.ApophiaPasswordChangeView.as_view(), name='password_change'),
    path('password-change/done/', views.ApophiaPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('staff-directory/', views.staff_directory, name='staff_directory'),
]
