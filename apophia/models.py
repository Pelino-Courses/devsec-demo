import os
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from .uploads import get_private_storage


# ------------------------------------------------------------------ #
# Upload path helpers — use UUID filenames to prevent enumeration and
# path-traversal attacks via crafted original filenames.
# ------------------------------------------------------------------ #

def _avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'avatars/{uuid.uuid4().hex}{ext}'


def _document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    # Shard by user PK so one user's documents stay in their own directory.
    return f'{instance.user_id}/{uuid.uuid4().hex}{ext}'


# ------------------------------------------------------------------ #
# Models
# ------------------------------------------------------------------ #

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    # blank/null so existing profiles are unaffected before a user uploads.
    avatar = models.ImageField(upload_to=_avatar_upload_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    # storage=get_private_storage is a *callable* so Django re-evaluates it on
    # every access, making override_settings work correctly in tests.
    file = models.FileField(upload_to=_document_upload_path, storage=get_private_storage)
    # Store the sanitised original name separately so users see a meaningful
    # filename on download without exposing the UUID path used on disk.
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.user.username})"


class LoginAttempt(models.Model):
    username = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Failed attempt for {self.username} from {self.ip_address} at {self.timestamp}"


# ------------------------------------------------------------------ #
# Signals
# ------------------------------------------------------------------ #

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=Profile)
def _delete_old_avatar(sender, instance, **kwargs):
    """Remove the old avatar file from storage when a new one is uploaded."""
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return
    old_name = old.avatar.name if old.avatar else None
    new_name = instance.avatar.name if instance.avatar else None
    if old_name and old_name != new_name:
        old.avatar.storage.delete(old_name)


@receiver(post_delete, sender=Document)
def _delete_document_file(sender, instance, **kwargs):
    """Remove the physical file when a Document record is deleted."""
    if instance.file:
        instance.file.delete(save=False)
