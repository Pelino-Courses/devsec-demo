from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extended user profile for authentication service.
    Links to Django's built-in User model with one-to-one relationship.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='antoine_profile')
    bio = models.TextField(blank=True, max_length=500)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class LoginHistory(models.Model):
    """
    Track user login history for security audit.
    Helpful for detecting suspicious activity.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-login_time']
        verbose_name_plural = 'Login Histories'
        indexes = [
            models.Index(fields=['user', '-login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class PasswordChangeHistory(models.Model):
    """
    Track password changes for security audit.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_changes')
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Password Change Histories'
    
    def __str__(self):
        return f"{self.user.username} - Password changed at {self.changed_at}"
