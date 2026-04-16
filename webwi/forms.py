from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import Profile


UserModel = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = UserModel
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'input', 'placeholder': 'Choose a username'})
        self.fields['email'].widget.attrs.update({'class': 'input', 'placeholder': 'Enter your email'})
        self.fields['password1'].widget.attrs.update({'class': 'input', 'placeholder': 'Create a strong password'})
        self.fields['password2'].widget.attrs.update({'class': 'input', 'placeholder': 'Repeat your password'})


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'input', 'placeholder': 'Your username'})
        self.fields['password'].widget.attrs.update({'class': 'input', 'placeholder': 'Your password'})


class PasswordUpdateForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'input', 'placeholder': 'Current password'})
        self.fields['new_password1'].widget.attrs.update({'class': 'input', 'placeholder': 'New password'})
        self.fields['new_password2'].widget.attrs.update({'class': 'input', 'placeholder': 'Repeat new password'})


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = Profile
        fields = ('display_name', 'bio', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['display_name'].widget.attrs.update({'class': 'input', 'placeholder': 'Public display name'})
        self.fields['bio'].widget.attrs.update({'class': 'textarea', 'placeholder': 'Tell us something about yourself'})
        self.fields['first_name'].widget.attrs.update({'class': 'input', 'placeholder': 'First name'})
        self.fields['last_name'].widget.attrs.update({'class': 'input', 'placeholder': 'Last name'})
        self.fields['email'].widget.attrs.update({'class': 'input', 'placeholder': 'Email address'})

        if user is not None:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True, user=None):
        profile = super().save(commit=commit)
        if user is not None:
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            if commit:
                user.save(update_fields=['first_name', 'last_name', 'email'])
        return profile
