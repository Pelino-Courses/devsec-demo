from django.urls import path

from . import views

app_name = 'mupenz_fulgence'

urlpatterns = [
    # Dashboard — protected home page
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Authentication lifecycle
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/',    views.UserLoginView.as_view(),    name='login'),
    path('logout/',   views.UserLogoutView.as_view(),   name='logout'),

    # Account management
    path('profile/',          views.ProfileView.as_view(),             name='profile'),
    path('password/change/',  views.UserPasswordChangeView.as_view(),  name='password_change'),
]
