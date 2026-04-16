import uuid
import os
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


def user_directory_path(instance, filename):
    """
    Generate a secure, isolated storage path for user-specific uploads.
    
    Format: uploads/user_<id>/<type>/<random_uuid>.<ext>
    
    This approach:
    1. Isolates users into subdirectories.
    2. Randomizes filenames to prevent information disclosure (enumeration).
    3. Mitigates potential directory traversal by stripping user-provided names.
    """
    ext = filename.split('.')[-1]
    
    # Determine the directory 'type' based on the field name
    # We can inspect the instance's field if needed, but for now simple check:
    # This is slightly simplified; in a larger app we might pass the type as a partial.
    if hasattr(instance, '_upload_type'):
        folder = instance._upload_type
    else:
        folder = 'general'
        
    random_filename = f"{uuid.uuid4()}.{ext}"
    return f'uploads/user_{instance.user.id}/{folder}/{random_filename}'


class UserProfile(models.Model):
    """
    Extended user profile model to store additional student information.
    
    This model extends Django's built-in User model with application-specific
    fields for student management while maintaining security best practices.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    student_id = models.CharField(
        max_length=20,
        unique=True,
        help_text=_('Unique student identifier')
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("Student's date of birth")
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Contact phone number')
    )
    bio = models.TextField(
        blank=True,
        max_length=500,
        help_text=_('Brief biography or about section')
    )
    
    # Secure file upload fields
    avatar = models.ImageField(
        upload_to=user_directory_path,
        null=True,
        blank=True,
        help_text=_('User profile picture (JPEG/PNG, max 2MB)')
    )
    academic_document = models.FileField(
        upload_to=user_directory_path,
        null=True,
        blank=True,
        help_text=_('Academic document (PDF/DOCX, max 5MB)')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.student_id})"

    def save(self, *args, **kwargs):
        # We can't easily pass 'folder' to the upload_to function directly
        # so we set a temporary attribute on the instance.
        super().save(*args, **kwargs)
