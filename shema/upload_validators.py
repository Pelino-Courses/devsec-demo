import os
from django.core.exceptions import ValidationError

# Magic bytes for allowed file types
AVATAR_MAGIC = {
    'jpg':  (b'\xff\xd8\xff', 'image/jpeg'),
    'png':  (b'\x89PNG\r\n\x1a\n', 'image/png'),
    'gif':  (b'GIF87a', 'image/gif'),
    'gif2': (b'GIF89a', 'image/gif'),
    'webp': (b'RIFF', 'image/webp'),
}
DOCUMENT_MAGIC = {
    'pdf': (b'%PDF', 'application/pdf'),
    'txt': None,  # no magic bytes; extension-only for plain text
}

ALLOWED_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.txt'}

MAX_AVATAR_SIZE = 2 * 1024 * 1024    # 2 MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5 MB


def _read_magic(f, n=12):
    f.seek(0)
    header = f.read(n)
    f.seek(0)
    return header


def validate_avatar(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValidationError(
            f"Avatar file type '{ext}' is not allowed. Use: jpg, png, gif, webp."
        )
    if file.size > MAX_AVATAR_SIZE:
        raise ValidationError("Avatar file must be 2 MB or smaller.")

    header = _read_magic(file)
    valid = (
        header[:3] == b'\xff\xd8\xff' or          # JPEG
        header[:8] == b'\x89PNG\r\n\x1a\n' or     # PNG
        header[:6] in (b'GIF87a', b'GIF89a') or   # GIF
        (header[:4] == b'RIFF' and header[8:12] == b'WEBP')  # WebP
    )
    if not valid:
        raise ValidationError(
            "File content does not match a recognised image format. "
            "Upload a real jpg, png, gif, or webp file."
        )


def validate_document(file):
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f"Document file type '{ext}' is not allowed. Use: pdf or txt."
        )
    if file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Document must be 5 MB or smaller.")

    if ext == '.pdf':
        header = _read_magic(file)
        if not header.startswith(b'%PDF'):
            raise ValidationError(
                "File content does not match PDF format. "
                "Upload a real PDF file."
            )
