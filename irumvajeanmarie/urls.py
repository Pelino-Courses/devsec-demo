from django.urls import path
from . import views

app_name = 'irumvajeanmarie'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('instructor/', views.instructor_panel, name='instructor_panel'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
]