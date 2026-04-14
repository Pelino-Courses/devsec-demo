from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('bio', 'avatar', 'document')
