from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'Munyabugingo'

urlpatterns = [
    # Registration
    path('register/', views.register, name='register'),
    
    # Login/Logout
    path('login/', views.SecureLoginView.as_view(), name='login'),
    path('logout/', views.SecureLogoutView.as_view(), name='logout'),
    
    # Dashboard (protected)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Password change
    path('password-change/', views.AuditPasswordChangeView.as_view(
        template_name='olivier/password_change.html'
    ), name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='olivier/password_change_done.html'
    ), name='password_change_done'),
    
    # Profile view
    path('profile/', views.profile, name='profile'),
    path('profile/<int:pk>/', views.profile_detail, name='profile_detail'),
    # Admin dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # Password Reset
    path('password-reset/', views.AuditPasswordResetView.as_view(
        template_name='olivier/password_reset_form.html',
        email_template_name='olivier/password_reset_email.html',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='olivier/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.AuditPasswordResetConfirmView.as_view(
        template_name='olivier/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='olivier/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # AJAX Endpoints
    path('api/toggle-like/', views.toggle_like, name='toggle_like'),
    
    # Secure File Management
    path('documents/', views.list_documents, name='list_documents'),
    path('documents/upload/', views.upload_document, name='upload_document'),
    path('documents/download/<int:pk>/', views.download_document, name='download_document'),
]