from django.urls import path
from . import views

app_name = 'jeanclaudeirumva'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('instructor/', views.instructor_area_view, name='instructor_area'),
    path('admin-area/', views.admin_area_view, name='admin_area'),
]