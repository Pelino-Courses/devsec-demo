from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


class Profile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	display_name = models.CharField(max_length=150, blank=True)
	bio = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		permissions = [
			('view_user_directory', 'Can view privileged user directory'),
		]

	def __str__(self):
		return self.display_name or self.user.get_username()


class LoginAttempt(models.Model):
    """Record of a single failed login attempt.

    Used to enforce account-level lockout after MAX_FAILED_ATTEMPTS
    consecutive failures within the LOCKOUT_DURATION window.
    Successful login clears all records for that username.
    """

    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['username', 'attempted_at'])]

    @classmethod
    def recent_count(cls, username):
        """Number of failed attempts for username within the lockout window."""
        since = timezone.now() - LOCKOUT_DURATION
        return cls.objects.filter(username=username, attempted_at__gte=since).count()

    @classmethod
    def is_locked(cls, username):
        return cls.recent_count(username) >= MAX_FAILED_ATTEMPTS

    @classmethod
    def record(cls, username, ip_address=None):
        cls.objects.create(username=username, ip_address=ip_address)

    @classmethod
    def clear(cls, username):
        cls.objects.filter(username=username).delete()
