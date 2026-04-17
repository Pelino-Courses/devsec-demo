from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import os


class Role(models.TextChoices):
    USER = 'user', 'Standard User'
    INSTRUCTOR = 'instructor', 'Instructor'
    STAFF = 'staff', 'Staff'
    ADMIN = 'admin', 'Administrator'


def validate_avatar_file(file):
    """Validate avatar uploads: size, extension, and MIME type."""
    # File size limit: 5MB
    if file.size > 5 * 1024 * 1024:
        raise ValidationError(f'Avatar file size must not exceed 5MB. Current: {file.size / (1024*1024):.1f}MB')
    
    # Allowed extensions
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    file_ext = os.path.splitext(file.name)[1][1:].lower()
    if file_ext not in allowed_extensions:
        raise ValidationError(f'Avatar file type not allowed. Allowed: {", ".join(allowed_extensions)}')
    
    # MIME type validation - check file signature/magic bytes
    file.seek(0)
    file_header = file.read(12)
    file.seek(0)
    
    # Magic byte checks for common image formats
    mime_checks = {
        b'\xFF\xD8\xFF': ['jpg', 'jpeg'],  # JPEG
        b'\x89PNG\r\n': ['png'],  # PNG
        b'GIF8': ['gif'],  # GIF
        b'RIFF': ['webp'],  # WebP (also check for WEBP string)
    }
    
    valid_mime = False
    for magic_bytes, exts in mime_checks.items():
        if file_header.startswith(magic_bytes):
            if file_ext in exts:
                valid_mime = True
                break
    
    if not valid_mime:
        raise ValidationError('Avatar file is not a valid image format. File does not match expected image signature.')


def validate_document_file(file):
    """Validate document uploads: size, extension, and MIME type."""
    # File size limit: 10MB
    if file.size > 10 * 1024 * 1024:
        raise ValidationError(f'Document file size must not exceed 10MB. Current: {file.size / (1024*1024):.1f}MB')
    
    # Allowed extensions
    allowed_extensions = ['pdf', 'doc', 'docx', 'txt', 'pptx', 'xlsx']
    file_ext = os.path.splitext(file.name)[1][1:].lower()
    if file_ext not in allowed_extensions:
        raise ValidationError(f'Document type not allowed. Allowed: {", ".join(allowed_extensions)}')
    
    # MIME type validation - check file signature
    file.seek(0)
    file_header = file.read(8)
    file.seek(0)
    
    # Magic byte checks
    mime_checks = {
        b'%PDF': ['pdf'],  # PDF
        b'PK\x03\x04': ['docx', 'xlsx', 'pptx'],  # Office Open XML
        b'\xd0\xcf\x11\xe0': ['doc'],  # Office 97-2003 (OLE)
    }
    
    valid_mime = False
    for magic_bytes, exts in mime_checks.items():
        if file_header.startswith(magic_bytes):
            if file_ext in exts:
                valid_mime = True
                break
    
    # Plain text files don't have magic bytes
    if file_ext == 'txt' and file_header:
        try:
            file_header.decode('utf-8')
            valid_mime = True
        except UnicodeDecodeError:
            pass
    
    if not valid_mime:
        raise ValidationError('Document file is not a valid document format. File does not match expected document signature.')


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/%d/',
        blank=True,
        validators=[validate_avatar_file],
        help_text='Upload a profile avatar image (jpg, png, gif, webp). Max 5MB.'
    )
    bio = models.TextField(blank=True, max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} Profile'

    @property
    def is_privileged(self):
        return self.role in [Role.INSTRUCTOR, Role.STAFF, Role.ADMIN]

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_user_permissions()

    def _update_user_permissions(self):
        privileged_group, _ = Group.objects.get_or_create(name='Privileged')
        standard_group, _ = Group.objects.get_or_create(name='Standard')

        if self.is_privileged:
            self.user.groups.add(privileged_group)
            self.user.groups.remove(standard_group)
            if not self.user.is_staff:
                self.user.is_staff = self.role == Role.ADMIN
                self.user.save(update_fields=['is_staff'])
        else:
            self.user.groups.add(standard_group)
            self.user.groups.remove(privileged_group)


class Document(models.Model):
    """Student-uploaded documents with secure handling."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/',
        validators=[validate_document_file],
        help_text='Upload a document (pdf, doc, docx, txt, pptx, xlsx). Max 10MB.'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, max_length=500)
    
    # Access control: only owner and staff can download
    is_public = models.BooleanField(default=False, help_text='Make visible to other users in profiles')

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f'{self.title} - {self.user.username}'


def create_role_groups():
    """Initialize role groups with appropriate permissions."""
    privileged_group, created = Group.objects.get_or_create(name='Privileged')
    standard_group, created = Group.objects.get_or_create(name='Standard')

    content_type = ContentType.objects.get_for_model(Profile)

    view_privileged_permission, _ = Permission.objects.get_or_create(
        codename='view_privileged',
        name='Can view privileged content',
        content_type=content_type,
    )
    manage_users_permission, _ = Permission.objects.get_or_create(
        codename='manage_users',
        name='Can manage users',
        content_type=content_type,
    )
    view_all_profiles_permission, _ = Permission.objects.get_or_create(
        codename='view_all_profiles',
        name='Can view all profiles',
        content_type=content_type,
    )

    privileged_group.permissions.add(
        view_privileged_permission,
        manage_users_permission,
        view_all_profiles_permission,
    )

    standard_group.permissions.add(view_privileged_permission)
