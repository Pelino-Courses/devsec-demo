from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/<str:username>/', views.profile_view, name='profile'),
    path('profile/<str:username>/update/', views.update_profile_view, name='update_profile'),
    path('profile/<str:username>/upload/avatar/', views.upload_avatar_view, name='upload_avatar'),
    path('profile/<str:username>/upload/document/', views.upload_document_view, name='upload_document'),
    path('profile/<str:username>/files/<str:filetype>/', views.serve_upload_view, name='serve_upload'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('instructor/', views.instructor_dashboard_view, name='instructor_dashboard'),
]
