from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Document

class CustomUserCreationForm(UserCreationForm):
    """Extended registration form including email and styling"""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 
        'placeholder': 'Email Address'
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ProfileUpdateForm(forms.ModelForm):
    """Update user fields"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class ProfileDataForm(forms.ModelForm):
    """Update profile-specific fields including avatar"""
    class Meta:
        model = Profile
        fields = ['bio', 'location', 'birth_date', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class DocumentUploadForm(forms.ModelForm):
    """Secure document upload form"""
    class Meta:
        model = Document
        fields = ['title', 'description', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }