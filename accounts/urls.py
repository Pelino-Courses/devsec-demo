from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='accounts_home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_view_by_id, name='profile_by_id'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('editor/panel/', views.editor_panel, name='editor_panel'),
]