from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User

from .models import UserProfile
from .validators import validate_avatar


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text='Required. Enter a valid email address.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class LoginForm(AuthenticationForm):
    pass


class UserPasswordChangeForm(PasswordChangeForm):
    pass


class BioForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio',)
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }
        help_texts = {
            'bio': 'Plain text only. Maximum 500 characters. HTML is not allowed.',
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'avatar')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }
        help_texts = {
            'bio': 'Plain text only. Maximum 500 characters.',
            'avatar': 'JPEG, PNG, or GIF only. Maximum 2MB.',
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            validate_avatar(avatar)
        return avatar