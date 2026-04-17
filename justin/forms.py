from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Document, validate_avatar_file, validate_document_file


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    """Secure profile form with file upload validation."""
    
    class Meta:
        model = Profile
        fields = ['avatar', 'bio']
        help_texts = {
            'avatar': 'Upload a profile picture (jpg, png, gif, webp). Max 5MB.',
            'bio': 'Brief bio or description (max 500 characters).',
        }
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }

    def clean_avatar(self):
        """Validate avatar file before saving."""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Re-validate even though model has validators
            validate_avatar_file(avatar)
        return avatar


class DocumentUploadForm(forms.ModelForm):
    """Secure document upload form with file validation."""
    
    class Meta:
        model = Document
        fields = ['title', 'file', 'description', 'is_public']
        help_texts = {
            'file': 'Upload a document (pdf, doc, docx, txt, pptx, xlsx). Max 10MB.',
            'title': 'Document title (max 255 characters).',
            'description': 'Brief description (optional, max 500 characters).',
            'is_public': 'Make this document visible in your public profile.',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Document title',
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.txt,.pptx,.xlsx',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description',
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_file(self):
        """Validate file upload before processing."""
        file = self.cleaned_data.get('file')
        if file:
            # Re-validate (model also validates)
            validate_document_file(file)
        return file

    def clean_title(self):
        """Ensure title is not empty and is reasonable."""
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError('Document title cannot be empty.')
        if len(title) > 255:
            raise forms.ValidationError('Document title is too long (max 255 characters).')
        return title
