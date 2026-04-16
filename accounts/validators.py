import os
from django.core.exceptions import ValidationError

def validate_max_file_size(value):
    """Limit file size to 5MB."""
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 5 MB.')

def validate_image_extension(value):
    """Ensure file is a valid image extension."""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    if not ext in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed: .jpg, .jpeg, .png, .gif')

def validate_document_extension(value):
    """Restrict document uploads to PDF and DOCX."""
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.docx']
    if not ext in valid_extensions:
        raise ValidationError('Unsupported document format. Allowed: .pdf, .docx')
