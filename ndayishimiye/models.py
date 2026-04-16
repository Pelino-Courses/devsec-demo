from django.db import models
from django.contrib.auth.models import User


def avatar_upload_path(instance, filename):
    return f'avatars/user_{instance.user.id}/{filename}'


def document_upload_path(instance, filename):
    return f'documents/user_{instance.user.id}/{filename}'


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile_ext'
    )
    bio = models.TextField(blank=True, default='')
    avatar = models.ImageField(
        upload_to=avatar_upload_path, blank=True, null=True
    )
    document = models.FileField(
        upload_to=document_upload_path, blank=True, null=True
    )

    def __str__(self):
        return f'Profile of {self.user.username}'
