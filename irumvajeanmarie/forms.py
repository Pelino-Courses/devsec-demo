from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Profile

# 2 MB
AVATAR_MAX_SIZE = 2 * 1024 * 1024
# 5 MB
DOCUMENT_MAX_SIZE = 5 * 1024 * 1024

ALLOWED_AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
DANGEROUS_EXTENSIONS = {
    '.php', '.exe', '.sh', '.py', '.js', '.rb', '.pl',
    '.bat', '.cmd', '.ps1', '.asp', '.aspx', '.jsp',
    '.cgi', '.htaccess', '.phtml',
}


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio']


class CustomPasswordChangeForm(PasswordChangeForm):
    pass


class AvatarUploadForm(forms.Form):
    avatar = forms.ImageField()

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if not avatar:
            return avatar

        # Check file size
        if avatar.size > AVATAR_MAX_SIZE:
            raise forms.ValidationError(
                f"Avatar file too large. Maximum size is {AVATAR_MAX_SIZE // (1024 * 1024)} MB."
            )

        # Extract extension
        import os
        ext = os.path.splitext(avatar.name)[1].lower()

        # Reject dangerous extensions first
        if ext in DANGEROUS_EXTENSIONS:
            raise forms.ValidationError(
                f"File type '{ext}' is not allowed for security reasons."
            )

        # Only allow whitelisted extensions
        if ext not in ALLOWED_AVATAR_EXTENSIONS:
            raise forms.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(sorted(ALLOWED_AVATAR_EXTENSIONS))}."
            )

        return avatar


class DocumentUploadForm(forms.Form):
    document = forms.FileField()

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if not document:
            return document

        # Check file size
        if document.size > DOCUMENT_MAX_SIZE:
            raise forms.ValidationError(
                f"Document too large. Maximum size is {DOCUMENT_MAX_SIZE // (1024 * 1024)} MB."
            )

        # Extract extension
        import os
        ext = os.path.splitext(document.name)[1].lower()

        # Reject dangerous extensions first
        if ext in DANGEROUS_EXTENSIONS:
            raise forms.ValidationError(
                f"File type '{ext}' is not allowed for security reasons."
            )

        # Only allow whitelisted extensions
        if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
            raise forms.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}."
            )

        return document