from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='nkotanyib/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='nkotanyib/logout.html', next_page='login'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='nkotanyib/password_change.html', success_url='/password_change/done/'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='nkotanyib/password_change_done.html'), name='password_change_done'),
    path('dashboard/', views.privileged_dashboard, name='privileged_dashboard'),
]
