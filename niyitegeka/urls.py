from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'niyitegeka'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.loginview, name='login'),
    path('logout/', views.logoutview, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('password-change/', views.passwordchange, name='passwordchange'),
    path('staff/', views.staffdashboard, name='staffdashboard'),
    path(
        'profile/<str:username>/',
        views.profiledetail,
        name='profiledetail'
    ),
    path('update-bio/', views.updatebio, name='updatebio'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='niyitegeka/password_reset.html',
            email_template_name='niyitegeka/password_reset_email.txt',
            success_url='/auth/password-reset/done/'
        ),
        name='passwordreset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='niyitegeka/password_reset_done.html'
        ),
        name='passwordresetdone'
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='niyitegeka/password_reset_confirm.html',
            success_url='/auth/password-reset/complete/'
        ),
        name='passwordresetconfirm'
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='niyitegeka/password_reset_complete.html'
        ),
        name='passwordresetcomplete'
    ),
]
