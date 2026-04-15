"""
File upload validators for secure avatar and document handling.

Validates file types, sizes, and content to prevent malicious uploads.
"""

import mimetypes
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile


# Security configuration for file uploads
class FileUploadConfig:
    """Configuration for secure file uploads."""
    
    # Maximum file sizes (in bytes)
    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB
    
    # Allowed MIME types for avatars
    ALLOWED_AVATAR_MIMETYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
    }
    
    # Allowed file extensions for avatars
    ALLOWED_AVATAR_EXTENSIONS = {
        '.jpg',
        '.jpeg',
        '.png',
        '.webp',
        '.gif',
    }
    
    # Allowed MIME types for documents
    ALLOWED_DOCUMENT_MIMETYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    
    # Allowed file extensions for documents
    ALLOWED_DOCUMENT_EXTENSIONS = {
        '.pdf',
        '.doc',
        '.docx',
        '.txt',
        '.xls',
        '.xlsx',
    }
    
    # Dangerous file types to always block
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.vbs', '.js',
        '.jar', '.zip', '.rar', '.7z', '.tar', '.gz', '.sh', '.bash',
        '.py', '.php', '.asp', '.aspx', '.jsp', '.html', '.htm',
    }
    
    # Dangerous MIME types
    DANGEROUS_MIMETYPES = {
        'application/x-msdownload',
        'application/x-msdos-program',
        'application/x-executable',
        'application/x-elf',
        'application/x-sh',
        'application/x-shellscript',
    }


def validate_avatar_file(file_obj: UploadedFile) -> None:
    """
    Validate avatar file for safe upload.
    
    Checks:
    - File size limit
    - File extension
    - MIME type
    - Magic bytes (file signature)
    
    Args:
        file_obj: UploadedFile object
    
    Raises:
        ValidationError: If file fails any validation check
    """
    if not file_obj:
        return
    
    # Check file size
    if file_obj.size > FileUploadConfig.MAX_AVATAR_SIZE:
        raise ValidationError(
            f'Avatar file size exceeds maximum of {FileUploadConfig.MAX_AVATAR_SIZE / 1024 / 1024:.1f} MB. '
            f'Your file is {file_obj.size / 1024 / 1024:.1f} MB.',
            code='file_too_large'
        )
    
    # Get file name and extension
    file_name = file_obj.name
    file_ext = get_file_extension(file_name)
    
    # Check extension
    if file_ext.lower() not in FileUploadConfig.ALLOWED_AVATAR_EXTENSIONS:
        raise ValidationError(
            f'Avatar file type "{file_ext}" is not allowed. '
            f'Allowed types: {", ".join(FileUploadConfig.ALLOWED_AVATAR_EXTENSIONS)}',
            code='invalid_extension'
        )
    
    # Check dangerous extensions
    if file_ext.lower() in FileUploadConfig.DANGEROUS_EXTENSIONS:
        raise ValidationError(
            f'File type "{file_ext}" is not allowed due to security restrictions.',
            code='dangerous_extension'
        )
    
    # Validate MIME type
    validate_mime_type(file_obj, FileUploadConfig.ALLOWED_AVATAR_MIMETYPES, 'avatar')
    
    # Validate magic bytes (file signature)
    validate_image_magic_bytes(file_obj)


def validate_document_file(file_obj: UploadedFile) -> None:
    """
    Validate document file for safe upload.
    
    Checks:
    - File size limit
    - File extension
    - MIME type
    - Magic bytes
    
    Args:
        file_obj: UploadedFile object
    
    Raises:
        ValidationError: If file fails any validation check
    """
    if not file_obj:
        return
    
    # Check file size
    if file_obj.size > FileUploadConfig.MAX_DOCUMENT_SIZE:
        raise ValidationError(
            f'Document file size exceeds maximum of {FileUploadConfig.MAX_DOCUMENT_SIZE / 1024 / 1024:.1f} MB. '
            f'Your file is {file_obj.size / 1024 / 1024:.1f} MB.',
            code='file_too_large'
        )
    
    # Get file extension
    file_name = file_obj.name
    file_ext = get_file_extension(file_name)
    
    # Check extension
    if file_ext.lower() not in FileUploadConfig.ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f'Document file type "{file_ext}" is not allowed. '
            f'Allowed types: {", ".join(FileUploadConfig.ALLOWED_DOCUMENT_EXTENSIONS)}',
            code='invalid_extension'
        )
    
    # Check dangerous extensions
    if file_ext.lower() in FileUploadConfig.DANGEROUS_EXTENSIONS:
        raise ValidationError(
            f'File type "{file_ext}" is not allowed due to security restrictions.',
            code='dangerous_extension'
        )
    
    # Validate MIME type
    validate_mime_type(file_obj, FileUploadConfig.ALLOWED_DOCUMENT_MIMETYPES, 'document')


def validate_mime_type(file_obj: UploadedFile, allowed_mimetypes: set, file_type: str) -> None:
    """
    Validate that file MIME type is allowed.
    
    Checks both:
    - guessed_type (from file extension)
    - content_type (from upload metadata)
    
    Args:
        file_obj: UploadedFile object
        allowed_mimetypes: Set of allowed MIME types
        file_type: Type of file (avatar/document) for error messages
    
    Raises:
        ValidationError: If MIME type is not allowed
    """
    # Check dangerous MIME types first
    if file_obj.content_type in FileUploadConfig.DANGEROUS_MIMETYPES:
        raise ValidationError(
            f'File MIME type "{file_obj.content_type}" is not allowed due to security restrictions.',
            code='dangerous_mimetype'
        )
    
    # Guess MIME type from file extension
    guessed_type, _ = mimetypes.guess_type(file_obj.name)
    
    # Verify MIME type is in allowed list
    if file_obj.content_type not in allowed_mimetypes and guessed_type not in allowed_mimetypes:
        raise ValidationError(
            f'{file_type.capitalize()} file MIME type "{file_obj.content_type}" is not allowed. '
            f'Allowed types: {", ".join(sorted(allowed_mimetypes))}',
            code='invalid_mimetype'
        )


def validate_image_magic_bytes(file_obj: UploadedFile) -> None:
    """
    Validate image file by checking magic bytes (file signature).
    
    This prevents files masquerading as images by checking actual file content,
    not just extension/MIME type.
    
    Supported formats and their signatures:
    - JPEG: FF D8 FF
    - PNG: 89 50 4E 47
    - GIF: 47 49 46 38 (GIF8)
    - WebP: RIFF ... WEBP
    
    Args:
        file_obj: UploadedFile object
    
    Raises:
        ValidationError: If magic bytes don't match image format
    """
    # Read file header to check magic bytes
    file_obj.seek(0)
    
    try:
        header = file_obj.read(12)  # Read first 12 bytes for signature check
    except Exception as e:
        raise ValidationError(
            'Unable to read file. Please ensure the file is valid.',
            code='file_read_error'
        ) from e
    finally:
        file_obj.seek(0)  # Reset file pointer
    
    if not header:
        raise ValidationError('File is empty.', code='empty_file')
    
    # Define magic bytes for valid image formats
    valid_signatures = {
        b'\xFF\xD8\xFF': 'JPEG',  # JPEG
        b'\x89\x50\x4E\x47': 'PNG',  # PNG
        b'\x47\x49\x46\x38': 'GIF',  # GIF87a or GIF89a
    }
    
    # Check for WebP (RIFF header with WEBP signature)
    if header.startswith(b'RIFF') and b'WEBP' in header:
        return  # Valid WebP
    
    # Check other formats
    for signature, format_name in valid_signatures.items():
        if header.startswith(signature):
            return  # Valid image
    
    raise ValidationError(
        'File is not a valid image. Uploaded file does not match a recognized image format.',
        code='invalid_image'
    )


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Name of file
    
    Returns:
        File extension in lowercase (e.g., '.jpg')
    """
    import os
    _, ext = os.path.splitext(filename)
    return ext


def sanitize_filename(filename: str) -> str:
    r"""
    Sanitize filename to prevent directory traversal and other attacks.
    
    Removes:
    - Path separators (/ \ .. etc)
    - Special characters
    - Null bytes
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename safe for storage
    """
    import os
    import re
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Get basename only (removes any path components)
    filename = os.path.basename(filename)
    
    # Remove dangerous characters but keep dots for extension
    # Keep alphanumeric, dots, hyphens, and underscores
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    
    # Remove leading/trailing dots or hyphens
    filename = filename.strip('.-_')
    
    return filename
