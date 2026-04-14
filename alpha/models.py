import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from .validators import validate_file_content, validate_file_size

def user_directory_path(instance, filename):
    # Route execution dynamically isolating namespaces and names into secure derivations 
    ext = os.path.splitext(filename)[1]
    return f'user_{instance.user.id}/files/{uuid.uuid4()}{ext}'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.FileField(upload_to=user_directory_path, validators=[validate_file_content, validate_file_size], blank=True, null=True)
    document = models.FileField(upload_to=user_directory_path, validators=[validate_file_content, validate_file_size], blank=True, null=True)

    class Meta:
        permissions = [
            ("can_view_dashboard", "Can view instructor dashboard"),
        ]

    def __str__(self):
        return self.user.username
