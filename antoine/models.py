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


class LoginAttempt(models.Model):
    """
    Track failed login attempts to prevent brute-force attacks.
    
    Implements progressive cooldowns:
    - 0-4 failures: No cooldown
    - 5-9 failures: 30 second cooldown
    - 10-14 failures: 1 minute cooldown
    - 15-19 failures: 5 minute cooldown
    - 20+ failures: 15 minute cooldown
    
    After account is locked, admins must manually unlock or user waits for cooldown.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='login_attempt')
    failed_attempts = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(auto_now=True)
    locked_until = models.DateTimeField(null=True, blank=True, help_text='Account locked until this time')
    is_locked = models.BooleanField(default=False, help_text='Manual lock by admin')
    
    class Meta:
        verbose_name_plural = 'Login Attempts'
        indexes = [
            models.Index(fields=['user', '-last_attempt']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.failed_attempts} failed attempts"
    
    def increment_failed_attempts(self):
        """Increment failed attempts and update lockout."""
        self.failed_attempts += 1
        self.last_attempt = timezone.now()
        
        # Lock after 5 failed attempts with progressive cooldowns
        if self.failed_attempts >= 5:
            # Progressive cooldown in seconds
            if self.failed_attempts < 10:
                cooldown = 30  # 30 seconds
            elif self.failed_attempts < 15:
                cooldown = 60  # 1 minute
            elif self.failed_attempts < 20:
                cooldown = 300  # 5 minutes
            else:
                cooldown = 900  # 15 minutes
            
            self.locked_until = timezone.now() + timezone.timedelta(seconds=cooldown)
        
        self.save()
    
    def reset_attempts(self):
        """Reset failed attempts after successful login."""
        self.failed_attempts = 0
        self.locked_until = None
        self.save()
    
    def is_temporarily_locked(self):
        """Check if account is temporarily locked due to failed attempts."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        # Clear expired lockout
        if self.locked_until and timezone.now() >= self.locked_until:
            self.locked_until = None
            self.save()
        return False
    
    def get_cooldown_seconds(self):
        """Get remaining cooldown in seconds."""
        if not self.locked_until:
            return 0
        remaining = (self.locked_until - timezone.now()).total_seconds()
        return max(0, int(remaining))


class AuditLog(models.Model):
    """
    Comprehensive audit logging for all authentication and privilege changes.
    
    Tracks security-relevant events without logging sensitive data:
    - User authentication (login success/failure)
    - User registration
    - User logout
    - Password changes and resets
    - Permission/role changes
    - Admin actions
    
    This model supports review, debugging, and compliance requirements.
    """
    
    # Event type choices
    EVENT_TYPES = [
        ('REGISTRATION', 'User Registration'),
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILURE', 'Login Failure'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('PASSWORD_RESET_REQUEST', 'Password Reset Request'),
        ('PASSWORD_RESET_CONFIRM', 'Password Reset Confirmed'),
        ('PERMISSION_CHANGE', 'Permission/Role Change'),
        ('PROFILE_UPDATE', 'Profile Update'),
        ('ADMIN_ACTION', 'Admin Action'),
        ('ACCOUNT_LOCK', 'Account Lock'),
        ('ACCOUNT_UNLOCK', 'Account Unlock'),
    ]
    
    # Severity levels
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs',
        help_text='User who triggered the event'
    )
    affected_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_affected',
        help_text='User affected by the event (may differ from user for admin actions)'
    )
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        help_text='Type of security event'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='MEDIUM',
        help_text='Severity level of the event'
    )
    ip_address = models.GenericIPAddressField(
        help_text='IP address where event originated'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string of the client'
    )
    description = models.TextField(
        help_text='Detailed description of the event'
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Structured data about the event (never contains passwords or secrets)'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the event occurred'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['affected_user', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
        ]
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        event_name = self.get_event_type_display()
        user_info = self.user.username if self.user else 'Anonymous'
        return f"{event_name} by {user_info} at {self.timestamp}"
