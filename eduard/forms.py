from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import UserProfile

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



class BioForm(forms.ModelForm):
    """
    Form for editing the user's bio.

    XSS fix: the bio field is a plain TextField with no HTML allowed.
    Django's ModelForm renders it as a standard textarea, and Django's
    template engine escapes the output automatically when rendered with
    {{ profile.bio }} — no |safe filter is used anywhere.
    """
    class Meta:
        model = UserProfile
        fields = ('bio',)
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }
        help_texts = {
            'bio': 'Plain text only. Maximum 500 characters. HTML is not allowed.',
        }