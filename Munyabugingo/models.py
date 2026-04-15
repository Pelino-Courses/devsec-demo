from django.db import models
from django.contrib.auth.models import User
from .validators import validate_file_size, validate_image_extension, validate_document_extension

class Profile(models.Model):
    """Extended user profile model with secure avatar upload"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True,
        validators=[validate_image_extension, validate_file_size]
    )

    class Meta:
        permissions = [
            ("can_view_admin_dashboard", "Can view administrative dashboard"),
        ]

    def __str__(self):
        return f'{self.user.username} Profile'

class Document(models.Model):
    """User-uploaded documents with access control and validation"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[validate_document_extension, validate_file_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.title} ({self.user.username})'
