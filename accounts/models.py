import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from .validators import validate_max_file_size, validate_image_extension, validate_document_extension

def avatar_upload_path(instance, filename):
    """Rename avatar to UUID to prevent path traversal and collisions."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('avatars/', filename)

def doc_upload_path(instance, filename):
    """Rename document to UUID."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('documents/', filename)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    avatar = models.ImageField(
        upload_to=avatar_upload_path, 
        validators=[validate_max_file_size, validate_image_extension],
        null=True, blank=True
    )
    document = models.FileField(
        upload_to=doc_upload_path,
        validators=[validate_max_file_size, validate_document_extension],
        null=True, blank=True
    )

    def __str__(self):
        return self.user.username
