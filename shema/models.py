import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .upload_validators import validate_avatar, validate_document


def avatar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'private/avatars/{uuid.uuid4().hex}{ext}'


def document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'private/documents/{uuid.uuid4().hex}{ext}'


class RoleBasedAccess(models.Model):
    """
    A dummy model used exclusively to register role-based access control
    permissions into the Django contenttypes system without creating tables.
    """
    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            ('view_instructor_dashboard', 'Can view instructor dashboard'),
        ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.FileField(
        upload_to=avatar_upload_path,
        blank=True,
        null=True,
        validators=[validate_avatar],
    )
    document = models.FileField(
        upload_to=document_upload_path,
        blank=True,
        null=True,
        validators=[validate_document],
    )

    def __str__(self):
        return f"{self.user.username}'s profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
