"""
Forms for user authentication and registration.
"""

import uuid

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

# Allowed image MIME types and their magic-byte signatures.
_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
_MAGIC_BYTES: dict[bytes, str] = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # RIFF????WEBP — checked further below
}
_MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


def _check_magic_bytes(data: bytes) -> bool:
    """Return True if the file starts with a recognised image magic sequence."""
    for magic, _ in _MAGIC_BYTES.items():
        if data.startswith(magic):
            # WebP: bytes 0-3 are RIFF, bytes 8-12 must be WEBP
            if magic == b"RIFF":
                return len(data) >= 12 and data[8:12] == b"WEBP"
            return True
    return False


def validate_avatar(f):
    """
    Validate an uploaded avatar file for type, extension, and size.

    Checks performed:
    1. File size ≤ 2 MB
    2. Extension is one of jpg/jpeg/png/gif/webp
    3. Magic bytes match an expected image format (prevents disguised executables)
    4. Filename is replaced with a safe UUID-based name to prevent path traversal
    """
    # 1. Size check (read at most _MAX_AVATAR_SIZE + 1 bytes to avoid loading huge files)
    f.seek(0, 2)  # seek to end
    size = f.tell()
    f.seek(0)
    if size > _MAX_AVATAR_SIZE:
        raise ValidationError(
            f"Avatar file too large (max {_MAX_AVATAR_SIZE // (1024 * 1024)} MB)."
        )

    # 2. Extension check
    ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension '.{ext}'. "
            f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}."
        )

    # 3. Magic-byte check (read first 12 bytes)
    header = f.read(12)
    f.seek(0)
    if not _check_magic_bytes(header):
        raise ValidationError(
            "File content does not match an allowed image format."
        )

    # 4. Sanitise filename: replace with a UUID so original names never reach disk
    safe_ext = "jpg" if ext == "jpeg" else ext
    f.name = f"{uuid.uuid4().hex}.{safe_ext}"


class AvatarUploadForm(forms.Form):
    """
    Secure avatar upload form.

    Validates file size (≤ 2 MB), extension (jpg/jpeg/png/gif/webp),
    and magic bytes before accepting an upload.
    """

    avatar = forms.FileField()

    def clean_avatar(self):
        f = self.cleaned_data["avatar"]
        validate_avatar(f)
        return f


class RegistrationForm(UserCreationForm):
    """
    Custom registration form extending Django's UserCreationForm.
    
    Adds email field and customizes the form for better UX.
    """
    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address.",
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "150 characters or fewer. Letters, digits and @/./+/-/_ only."
        self.fields['password1'].help_text = (
            "Your password must contain at least 8 characters and "
            "can't be entirely numeric."
        )
        self.fields['password2'].help_text = "Enter the same password again for verification."
    
    def clean_email(self):
        """Validate that email is unique across users."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email
    
    def clean_username(self):
        """Validate that username is unique."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username
    
    def save(self, commit=True):
        """Save the user with email."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
