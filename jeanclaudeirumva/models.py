import os
from django.db import models
from django.contrib.auth.models import User


def avatar_upload_path(instance, filename):
    """Store avatars in a user-specific folder."""
    ext = os.path.splitext(filename)[1].lower()
    return f"avatars/user_{instance.user.id}{ext}"


def document_upload_path(instance, filename):
    """Store documents in a user-specific folder."""
    return f"documents/user_{instance.user.id}_{filename}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)
    document = models.FileField(upload_to=document_upload_path, blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"