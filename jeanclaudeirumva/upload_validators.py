import os
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_avatar(file):
    """Validate avatar file size and extension."""
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"Avatar file size must not exceed 2MB. "
            f"Your file is {file.size // (1024 * 1024)}MB."
        )

    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_AVATAR_EXTENSIONS:
        raise ValidationError(
            f"Avatar must be one of these formats: "
            f"{', '.join(settings.ALLOWED_AVATAR_EXTENSIONS)}. "
            f"You uploaded: {ext}"
        )

    # Check MIME type
    if hasattr(file, 'content_type'):
        if file.content_type not in settings.ALLOWED_AVATAR_MIME_TYPES:
            raise ValidationError(
                f"Invalid avatar file type: {file.content_type}"
            )


def validate_document(file):
    """Validate document file size and extension."""
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(
            f"Document file size must not exceed 2MB. "
            f"Your file is {file.size // (1024 * 1024)}MB."
        )

    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f"Document must be one of these formats: "
            f"{', '.join(settings.ALLOWED_DOCUMENT_EXTENSIONS)}. "
            f"You uploaded: {ext}"
        )

    # Check MIME type
    if hasattr(file, 'content_type'):
        if file.content_type not in settings.ALLOWED_DOCUMENT_MIME_TYPES:
            raise ValidationError(
                f"Invalid document file type: {file.content_type}"
            )