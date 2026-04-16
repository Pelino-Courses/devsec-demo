"""
Forms for user authentication and registration.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError


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
