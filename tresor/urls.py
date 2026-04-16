from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'tresor'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile_view, name='profile_view'),
    path('profile/<str:username>/edit/', views.profile_edit, name='profile_edit'),
    path('password-change/', views.password_change, name='password_change'),
    path('password-change/done/', views.password_change_done, name='password_change_done'),
    path('avatar/upload/', views.avatar_upload, name='avatar_upload'),
    path('documents/', views.documents, name='documents'),
    path('documents/<int:pk>/download/', views.document_download, name='document_download'),
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='tresor/password_reset_request.html',
            email_template_name='tresor/password_reset_email.txt',
            subject_template_name='tresor/password_reset_subject.txt',
            success_url='/tresor/password-reset/sent/',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='tresor/password_reset_sent.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='tresor/password_reset_confirm.html',
            success_url='/tresor/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='tresor/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
