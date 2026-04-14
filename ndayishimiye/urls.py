from django.urls import path
from . import views

app_name = 'ndayishimiye'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password-change/', views.password_change, name='password_change'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
]
