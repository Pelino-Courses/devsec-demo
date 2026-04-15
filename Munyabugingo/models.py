from django.db import models
from django.contrib.auth.models import User
from .validators import validate_file_size, validate_image_extension, validate_document_extension

class Profile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, validators=[validate_file_size, validate_image_extension])

    class Meta:
        permissions = [
            ("can_view_admin_dashboard", "Can view administrative dashboard"),
        ]

    def __str__(self):
        return f'{self.user.username} Profile'

class Document(models.Model):
    """Secure document storage model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/', validators=[validate_file_size, validate_document_extension])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
