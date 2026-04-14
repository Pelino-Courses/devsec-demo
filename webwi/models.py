from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

try:
    from PIL import Image
    _PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PILLOW_AVAILABLE = False

_ALLOWED_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
_MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


def _avatar_upload_path(instance, filename):
    """Store avatars under a UUID hex name to prevent enumeration."""
    ext = Path(filename).suffix.lower()
    return f'avatars/{uuid4().hex}{ext}'


def validate_avatar_upload(file):
    """Reject uploads that are oversized, have a disallowed extension, or are not valid images."""
    if file.size > _MAX_AVATAR_BYTES:
        raise ValidationError(
            f'Avatar must be smaller than 2 MB (received {file.size // 1024} KB).'
        )

    ext = Path(file.name).suffix.lower()
    if ext not in _ALLOWED_AVATAR_EXTENSIONS:
        raise ValidationError(
            f'File type "{ext}" is not allowed. Upload a JPG, PNG, GIF, or WebP image.'
        )

    if _PILLOW_AVAILABLE:
        try:
            img = Image.open(file)
            img.verify()
        except Exception:
            raise ValidationError('The uploaded file is not a valid image.')
        finally:
            # verify() closes the file; reset so downstream code can read it.
            file.seek(0)


MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


class Profile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	display_name = models.CharField(max_length=150, blank=True)
	bio = models.TextField(blank=True)
	avatar = models.FileField(
        upload_to=_avatar_upload_path,
        blank=True,
        null=True,
        validators=[validate_avatar_upload],
    )
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
