from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import os

def validate_file_size(value):
    filesize = value.size

    if filesize > 5 * 1024 * 1024: # 5MB limit
        raise ValidationError("The maximum file size that can be uploaded is 5MB")
    return value

def validate_is_image(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed: jpg, jpeg, png, gif')

def validate_is_document(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.doc', '.docx', '.txt']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed: pdf, doc, docx, txt')

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        validators=[validate_file_size, validate_is_image],
        null=True,
        blank=True
    )
    document = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[validate_file_size, validate_is_document],
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.user.username}'s Profile"
