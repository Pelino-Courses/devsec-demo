from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'irumvajeanmarie'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<str:username>/', views.view_profile, name='view_profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='irumvajeanmarie/password_reset.html',
        email_template_name='irumvajeanmarie/password_reset_email.html',
        success_url=reverse_lazy('irumvajeanmarie:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='irumvajeanmarie/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='irumvajeanmarie/password_reset_confirm.html',
        success_url=reverse_lazy('irumvajeanmarie:password_reset_complete')
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='irumvajeanmarie/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('instructor/', views.instructor_panel, name='instructor_panel'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('contact/', views.contact_view, name='contact'),
    path('contact-page/', views.contact_page_view, name='contact_page'),
    path('upload/avatar/', views.upload_avatar, name='upload_avatar'),
    path('upload/document/', views.upload_document, name='upload_document'),
    path('upload/document/<int:document_id>/delete/', views.delete_document, name='delete_document'),
]