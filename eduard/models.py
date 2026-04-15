from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class LoginAttempt(models.Model):
    """
    Tracks failed login attempts per username.

    Design choice: tracking by username rather than IP address because
    IP-based blocking is unreliable behind NATs and proxies, and can
    lock out innocent users sharing an IP. Username-based lockout
    targets the specific account being attacked.

    Trade-off: an attacker who knows a valid username can lock that
    user out deliberately (denial of service). This is mitigated by
    the short lockout window (15 minutes) and the password reset flow
    available to locked-out users.
    """
    username = models.CharField(max_length=150, db_index=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Login attempt'
        verbose_name_plural = 'Login attempts'

    def __str__(self):
        return f'{self.username} - {self.failed_attempts} failed attempts'

    def is_locked(self):
        """Return True if the account is currently locked out."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def seconds_until_unlock(self):
        """Return remaining lockout seconds, or 0 if not locked."""
        if self.locked_until:
            remaining = (self.locked_until - timezone.now()).total_seconds()
            return max(0, int(remaining))
        return 0

    def record_failure(self):
        """
        Increment the failed attempt counter. Lock the account for
        15 minutes once the threshold of 5 attempts is reached.
        """
        self.failed_attempts += 1
        self.last_failed_at = timezone.now()
        if self.failed_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=15)
        self.save()

    def clear(self):
        """Reset all counters on successful login."""
        self.failed_attempts = 0
        self.last_failed_at = None
        self.locked_until = None
        self.save()


def avatar_upload_path(instance, filename):
    """
    Store avatars in a per-user subdirectory with a randomised filename.
    The original filename is discarded to prevent path traversal and
    filename-based attacks.
    """
    from .validators import safe_filename
    return f'avatars/user_{instance.user.id}/{safe_filename(filename)}'


class UserProfile(models.Model):
    """
    Extends the built-in User with a bio field and avatar upload.

    XSS risk: bio field must never be rendered with |safe.
    Upload risk: avatar is validated by extension, size, and magic bytes
    before saving. The filename is randomised on storage.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile'
    )
    bio = models.TextField(blank=True, max_length=500)
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'

    def __str__(self):
        return f'Profile for {self.user.username}'
