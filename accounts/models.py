from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended user profile with role information."""
    ROLE_CHOICES = [
        ('viewer', 'Viewer'),
        ('editor', 'Editor'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"

class AuditLog(models.Model):
    """
    Model for persistent audit logging of security-relevant events.
    
    Security design:
    - Tracks who did what, when, and from where (IP).
    - Uses a generic 'details' field for extra context without leaking secrets.
    """
    EVENT_TYPES = [
        ('registration', 'User Registration'),
        ('login_success', 'Login Success'),
        ('login_failure', 'Login Failure'),
        ('logout', 'User Logout'),
        ('privilege_change', 'Privilege Change'),
        ('password_change', 'Password Change'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    username_attempted = models.CharField(max_length=150, blank=True, help_text="Used for login failures")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        user_part = self.user.username if self.user else self.username_attempted or "Anonymous"
        return f"[{self.timestamp}] {self.event_type}: {user_part}"
