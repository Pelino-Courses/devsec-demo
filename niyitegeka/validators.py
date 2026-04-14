from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx']
MAX_FILE_SIZE_MB = 2
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file_extension(value):
    ext = value.name.split('.')[-1].lower()
    allowed = ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS
    if ext not in allowed:
        raise ValidationError(
            f'File type .{ext} is not allowed. '
            f'Allowed types are: {", ".join(allowed)}'
        )


def validate_file_size(value):
    if value.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f'File size must not exceed {MAX_FILE_SIZE_MB}MB. '
            f'Your file is {value.size / (1024 * 1024):.1f}MB.'
        )


def validate_image_extension(value):
    ext = value.name.split('.')[-1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'File type .{ext} is not allowed for avatars. '
            f'Allowed types are: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
        )
