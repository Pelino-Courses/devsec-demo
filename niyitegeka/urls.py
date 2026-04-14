from django.urls import path
from . import views

app_name = 'niyitegeka'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.loginview, name='login'),
    path('logout/', views.logoutview, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('password-change/', views.passwordchange, name='passwordchange'),
]