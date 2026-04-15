from django.urls import path
from .views import register_view, login_view, logout_view, profile_view, change_password, update_profile_view, home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', update_profile_view, name='update_profile'),
    path('password-change/', change_password, name='password_change'),
]