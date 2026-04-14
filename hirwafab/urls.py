from django.urls import path
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
]
