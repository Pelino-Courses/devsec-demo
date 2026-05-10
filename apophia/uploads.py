"""
Upload validation and private storage for avatar and document uploads.

Validation layers applied to every upload:
  - Extension whitelist  (extension must match an allowed set)
  - File-size limit      (reject before touching file content)
  - Content check        (Pillow verify for images; magic bytes for PDFs;
                          UTF-8 decode probe for plain text)

Never trust the Content-Type header supplied by the browser — it is
client-controlled and trivially spoofed.  All content checks read from
the file stream itself.

Storage separation:
  - Avatars  → Django default storage (MEDIA_ROOT/avatars/).  Files are
               publicly accessible via MEDIA_URL, which is appropriate for
               profile photos.
  - Documents → private_storage (PRIVATE_STORAGE_ROOT/).  This root is
               intentionally *not* exposed under MEDIA_URL.  All downloads
               go through an authenticated Django view that enforces
               ownership before opening the file.
"""

import os

from django.core.exceptions import ValidationError

# ------------------------------------------------------------------ #
# Limits and whitelists
# ------------------------------------------------------------------ #

AVATAR_MAX_BYTES = 2 * 1024 * 1024          # 2 MB
AVATAR_ALLOWED_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.webp'})

DOCUMENT_MAX_BYTES = 5 * 1024 * 1024        # 5 MB
DOCUMENT_ALLOWED_EXTENSIONS = frozenset({'.pdf', '.txt'})

_PDF_MAGIC = b'%PDF'


# ------------------------------------------------------------------ #
# Private storage factory
# Used as storage=get_private_storage on Document.file so that each
# call reads the current settings value — essential for test isolation
# via override_settings(PRIVATE_STORAGE_ROOT=...).
# ------------------------------------------------------------------ #

def get_private_storage():
    """Return a FileSystemStorage rooted at PRIVATE_STORAGE_ROOT.

    base_url=None ensures no public URL is ever generated for stored
    files.  All access must go through the document_download view.
    """
    from django.conf import settings
    from django.core.files.storage import FileSystemStorage

    location = getattr(settings, 'PRIVATE_STORAGE_ROOT', settings.BASE_DIR / 'private')
    return FileSystemStorage(location=str(location), base_url=None)


# ------------------------------------------------------------------ #
# Public validators
# ------------------------------------------------------------------ #

def validate_avatar(upload):
    """Validate an avatar upload: extension, size, and image content."""
    _check_extension(upload.name, AVATAR_ALLOWED_EXTENSIONS)
    _check_size(upload, AVATAR_MAX_BYTES)
    _check_image_content(upload)


def validate_document(upload):
    """Validate a document upload: extension, size, and content magic."""
    _check_extension(upload.name, DOCUMENT_ALLOWED_EXTENSIONS)
    _check_size(upload, DOCUMENT_MAX_BYTES)
    ext = os.path.splitext(upload.name)[1].lower()
    if ext == '.pdf':
        _check_pdf_magic(upload)
    elif ext == '.txt':
        _check_text_encoding(upload)


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _check_extension(filename, allowed):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        friendly = ', '.join(sorted(allowed))
        raise ValidationError(
            f"File type \"{ext or '(none)'}\" is not allowed. "
            f"Accepted types: {friendly}."
        )


def _check_size(upload, max_bytes):
    if upload.size > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ValidationError(
            f"File size {upload.size:,} B exceeds the {limit_mb} MB limit."
        )


def _check_image_content(upload):
    """Open and verify the upload with Pillow.

    PIL.Image.verify() performs a more thorough integrity check than
    open() alone — it detects truncated files and mismatched headers.
    After verify() the image object is exhausted, so we always seek
    back to 0 in the finally block to leave the stream readable for
    Django's own ImageField processing.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        upload.seek(0)
        img = Image.open(upload)
        img.verify()
    except (UnidentifiedImageError, Exception):
        raise ValidationError(
            "The uploaded file is not a valid image or its content is corrupt."
        )
    finally:
        upload.seek(0)


def _check_pdf_magic(upload):
    """Confirm the file starts with the PDF magic bytes (%PDF)."""
    upload.seek(0)
    header = upload.read(4)
    upload.seek(0)
    if header != _PDF_MAGIC:
        raise ValidationError(
            "The uploaded file does not appear to be a valid PDF."
        )


def _check_text_encoding(upload):
    """Confirm the file (first 64 KB) is valid UTF-8."""
    upload.seek(0)
    raw = upload.read(65536)
    upload.seek(0)
    try:
        raw.decode('utf-8')
    except UnicodeDecodeError:
        raise ValidationError(
            "The text file must be encoded as UTF-8."
        )
