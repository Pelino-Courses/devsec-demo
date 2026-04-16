import os
from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}

ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif'}

# Magic bytes for allowed image formats
# These are read from the actual file content, not from the client header.
# An attacker cannot fake these by renaming a file or changing Content-Type.
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
}


def validate_avatar(file):
    """
    Validate an uploaded avatar file against three independent checks:

    1. File extension - rejects files with dangerous extensions
    2. File size - rejects files over MAX_UPLOAD_SIZE (2MB default)
    3. Magic bytes - reads the first bytes of the file to confirm
       the actual format matches an allowed image type regardless
       of what the client claimed in Content-Type or the filename

    All three checks must pass. Relying on only one (e.g. extension
    alone) can be bypassed by renaming a file or spoofing headers.
    """
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 2 * 1024 * 1024)

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'File type not allowed. Allowed types: '
            f'{", ".join(sorted(ALLOWED_EXTENSIONS))}'
        )

    if file.size > max_size:
        raise ValidationError(
            f'File too large. Maximum size is {max_size // (1024 * 1024)}MB.'
        )

    file.seek(0)
    header = file.read(16)
    file.seek(0)

    matched = False
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            matched = True
            break

    if not matched:
        raise ValidationError(
            'File content does not match an allowed image format. '
            'Upload a real JPEG, PNG, or GIF image.'
        )


def safe_filename(filename):
    """
    Return a UUID-based filename with the original extension.
    Prevents path traversal attacks and filename-based attacks
    by discarding the original filename entirely.
    """
    import uuid
    ext = os.path.splitext(filename)[1].lower()
    return f'{uuid.uuid4().hex}{ext}'