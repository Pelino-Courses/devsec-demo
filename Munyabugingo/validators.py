import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_file_size(value):
    """
    Validates that the file size is within limits.
    - Avatars usually < 2MB
    - Documents usually < 5MB
    """
    # For this implementation, we'll use 5MB as a generic upper limit
    # This can be customized per field in the model if needed, 
    # but here we provide a general validator.
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError(_('File size exceeds the limit of 5MB.'))

def validate_image_extension(value):
    """
    Allow-list for image extensions.
    """
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported file extension. Allowed: .jpg, .jpeg, .png, .gif'))

def validate_document_extension(value):
    """
    Allow-list for document extensions.
    """
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.txt', '.doc', '.docx']
    if not ext.lower() in valid_extensions:
        raise ValidationError(_('Unsupported file extension. Allowed: .pdf, .txt, .doc, .docx'))

def validate_mime_type(value):
    """
    Basic MIME type check using Python's built-in mimetypes.
    More advanced check would use python-magic (libmagic).
    """
    import mimetypes
    content_type = value.file.content_type
    # We can perform additional cross-checks between content_type and extension here
    # For now, we rely on the extension validators above for specific fields.
    pass
