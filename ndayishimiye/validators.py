from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.docx']
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_IMAGE_MIME_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
]

ALLOWED_DOCUMENT_MIME_TYPES = [
    'application/pdf',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]


def validate_avatar(file):
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file extension. Allowed: '
            f'{", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        )
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f'File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.'
        )
    if hasattr(file, 'content_type'):
        if file.content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValidationError(
                'Unsupported file type.'
            )


def validate_document(file):
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file extension. Allowed: '
            f'{", ".join(ALLOWED_DOCUMENT_EXTENSIONS)}'
        )
    if file.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f'File too large. Maximum size is {MAX_FILE_SIZE_MB}MB.'
        )
    if hasattr(file, 'content_type'):
        if file.content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
            raise ValidationError(
                'Unsupported file type.'
            )
