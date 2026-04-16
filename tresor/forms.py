import os

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, AVATAR_MAX_BYTES, DOCUMENT_MAX_BYTES

_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
_DOCUMENT_EXTENSIONS = {'.pdf', '.txt'}

_AVATAR_SIGNATURES = [
    (b'\xff\xd8\xff', 'jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'png'),
    (b'GIF87a', 'gif'),
    (b'GIF89a', 'gif'),
]


def _image_magic(f):
    header = f.read(16)
    f.seek(0)
    for sig, fmt in _AVATAR_SIGNATURES:
        if header.startswith(sig):
            return fmt
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return 'webp'
    return None


def _pdf_magic(f):
    header = f.read(5)
    f.seek(0)
    return 'pdf' if header.startswith(b'%PDF-') else None


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    pass


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = Profile
        fields = ('bio',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.save()
        if commit:
            profile.save()
        return profile


class AvatarUploadForm(forms.Form):
    avatar = forms.FileField()

    def clean_avatar(self):
        f = self.cleaned_data['avatar']
        if f.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError('Avatar must be 2 MB or smaller.')
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in _AVATAR_EXTENSIONS:
            raise forms.ValidationError('Allowed types: JPEG, PNG, GIF, WebP.')
        if _image_magic(f) is None:
            raise forms.ValidationError('File content does not match an allowed image format.')
        return f


class DocumentUploadForm(forms.Form):
    document = forms.FileField()

    def clean_document(self):
        f = self.cleaned_data['document']
        if f.size > DOCUMENT_MAX_BYTES:
            raise forms.ValidationError('Document must be 5 MB or smaller.')
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in _DOCUMENT_EXTENSIONS:
            raise forms.ValidationError('Allowed types: PDF, TXT.')
        if ext == '.pdf' and _pdf_magic(f) is None:
            raise forms.ValidationError('File content does not match PDF format.')
        return f
