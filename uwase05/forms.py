import os

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class ProfileUploadForm(forms.Form):
    avatar = forms.FileField(
        required=False,
        help_text='Allowed image types: PNG, JPEG, GIF. Max 2MB.',
    )
    document = forms.FileField(
        required=False,
        help_text='Allowed document types: PDF, TXT. Max 5MB.',
    )

    MAX_AVATAR_SIZE = 2 * 1024 * 1024
    MAX_DOCUMENT_SIZE = 5 * 1024 * 1024
    AVATAR_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
    DOCUMENT_EXTENSIONS = {'.pdf', '.txt'}

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar:
            return avatar

        self._validate_file_size(avatar, self.MAX_AVATAR_SIZE, 'avatar')
        extension = self._file_extension(avatar.name)
        if extension not in self.AVATAR_EXTENSIONS:
            raise forms.ValidationError('Allowed avatar file types: PNG, JPEG, GIF.')

        avatar.seek(0)
        if not self._is_valid_image(avatar, extension):
            raise forms.ValidationError('Uploaded avatar does not appear to be a valid image.')
        avatar.seek(0)

        return avatar

    def _is_valid_image(self, uploaded_file, extension):
        uploaded_file.seek(0)
        header = uploaded_file.read(10)
        uploaded_file.seek(0)

        if extension == '.png':
            return header.startswith(b'\x89PNG\r\n\x1a\n')
        if extension in {'.jpg', '.jpeg'}:
            return header.startswith(b'\xff\xd8\xff')
        if extension == '.gif':
            return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
        return False

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if not document:
            return document

        self._validate_file_size(document, self.MAX_DOCUMENT_SIZE, 'document')
        extension = self._file_extension(document.name)
        if extension not in self.DOCUMENT_EXTENSIONS:
            raise forms.ValidationError('Allowed document file types: PDF or TXT.')

        document.seek(0)
        header = document.read(8)
        document.seek(0)

        if extension == '.pdf':
            if not header.startswith(b'%PDF'):
                raise forms.ValidationError('Uploaded document does not appear to be a valid PDF.')
        elif extension == '.txt':
            if b'\x00' in header:
                raise forms.ValidationError('Uploaded text document appears to be binary.')

        return document

    def _validate_file_size(self, uploaded_file, max_bytes, field_name):
        if uploaded_file.size > max_bytes:
            raise forms.ValidationError(
                f'The {field_name} file may not be larger than {max_bytes // 1024} KB.'
            )

    def _file_extension(self, filename):
        return os.path.splitext(filename)[1].lower()
