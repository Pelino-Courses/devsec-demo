from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.FileField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} profile"

    class Meta:
        permissions = [
            ("can_view_all_profiles", "Can view all user profiles"),
            ("can_manage_users", "Can promote or demote users"),
        ]


class LoginAttempt(models.Model):
    """Track login attempts per user for brute-force protection."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_attempts', null=True, blank=True)
    username = models.CharField(max_length=150)  # Store for failed attempts (user not found)
    ip_address = models.GenericIPAddressField()
    attempt_timestamp = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['username', 'attempt_timestamp']),
            models.Index(fields=['user', 'attempt_timestamp']),
            models.Index(fields=['ip_address', 'attempt_timestamp']),
        ]
        ordering = ['-attempt_timestamp']
    
    def __str__(self):
        status = "✓" if self.is_successful else "✗"
        return f"{status} {self.username} @ {self.ip_address} ({self.attempt_timestamp})"
