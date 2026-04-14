from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('jeanclaudeirumva.urls')),
    path('auth/password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='jeanclaudeirumva/password_reset.html',
             email_template_name='jeanclaudeirumva/password_reset_email.html',
             subject_template_name='jeanclaudeirumva/password_reset_subject.txt',
         ),
         name='password_reset'),
    path('auth/password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='jeanclaudeirumva/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('auth/password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='jeanclaudeirumva/password_reset_confirm.html',
         ),
         name='password_reset_confirm'),
    path('auth/password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='jeanclaudeirumva/password_reset_complete.html',
         ),
         name='password_reset_complete'),
]