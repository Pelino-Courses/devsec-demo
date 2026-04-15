import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_size(value):
    """Limit files to 5MB"""
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError(_('File size exceeds the limit of 5MB.'))

def validate_image_extension(value):
    """Allow-list for images"""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
        raise ValidationError(_('Unsupported file extension. Allowed: .jpg, .jpeg, .png, .gif'))

def validate_document_extension(value):
    """Allow-list for documents"""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ['.pdf', '.txt', '.doc', '.docx']:
        raise ValidationError(_('Unsupported file extension. Allowed: .pdf, .txt, .doc, .docx'))
