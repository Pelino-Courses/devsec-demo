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
]