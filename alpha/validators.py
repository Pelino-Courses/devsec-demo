from django.core.exceptions import ValidationError
import os

def validate_file_size(value):
    limit = 2 * 1024 * 1024 # 2 MegaBytes
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 2 MB.')

def validate_file_content(file):
    # Retrieve physical byte signatures mapped intrinsically protecting extensions
    header = file.read(2048)
    file.seek(0)
    
    # Check explicitly defined physical execution structures structurally mapped
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    elif header.startswith(b'%PDF-'):
        return 'pdf'
    
    raise ValidationError("File type is not supported. Only exact PNG, JPEG, and PDF formatting is permitted structurally.")
