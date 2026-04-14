from django.urls import path
from . import views

app_name = 'mucyo_aime_maxime'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('password-change/', views.password_change_view, name='password_change'),
    
    # Staff-only routes
    path('staff/dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
    
    # Instructor-only routes
    path('instructor/reports/', views.instructor_reports_view, name='instructor_reports'),
]
