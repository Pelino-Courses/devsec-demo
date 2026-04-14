from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    
    email = forms.EmailField(
        required=True,
        help_text='Required. Enter a valid email address.',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        """Ensure the email address is not already in use."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email


class LoginForm(AuthenticationForm):
    
    pass


class UserPasswordChangeForm(PasswordChangeForm):
   
    pass