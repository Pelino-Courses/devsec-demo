from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extended user profile to store additional user information.
    Uses Django's built-in User model for authentication.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, max_length=500)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hirwafab_user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        permissions = [
            ('view_dashboard', 'Can view dashboard'),
            ('view_own_profile', 'Can view own profile'),
            ('change_own_profile', 'Can edit own profile'),
            ('change_own_password', 'Can change own password'),
            ('view_user_directory', 'Can view user directory'),
            ('view_all_profiles', 'Can view all profiles'),
            ('view_user_activity', 'Can view user activity'),
            ('download_reports', 'Can download reports'),
        ]

    def __str__(self):
        return f"Profile for {self.user.username}"
