from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='justin/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', 
         auth_views.PasswordChangeView.as_view(
             template_name='justin/change_password.html',
             success_url='/profile/'
         ), 
         name='change_password'),
    path('upload-document/', views.upload_document, name='upload_document'),
    path('document/<int:doc_id>/download/', views.download_document, name='download_document'),
    path('document/<int:doc_id>/delete/', views.delete_document, name='delete_document'),
    path('profiles/', views.all_profiles, name='all_profiles'),
    path('user/<int:user_id>/role/', views.change_user_role, name='change_user_role'),
]
