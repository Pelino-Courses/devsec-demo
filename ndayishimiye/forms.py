from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordChangeForm
)
from django.contrib.auth.models import User
from .models import UserProfile
from .validators import validate_avatar, validate_document


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class LoginForm(AuthenticationForm):
    pass


class CustomPasswordChangeForm(PasswordChangeForm):
    pass


class ProfileBioForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
        }


class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            validate_avatar(avatar)
        return avatar


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['document']

    def clean_document(self):
        document = self.cleaned_data.get('document')
        if document:
            validate_document(document)
        return document
