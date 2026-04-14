from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class RegistrationForm(UserCreationForm):
    """
    Extended registration form that collects email (required),
    first name, and last name in addition to the standard fields.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
        }),
        help_text='Required. A confirmation may be sent to this address.',
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'given-name',
            'class': 'form-control',
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'family-name',
            'class': 'form-control',
        }),
    )

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'autocomplete': 'username',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap class to password fields rendered by UserCreationForm
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email address already exists.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Updates both User (first_name, last_name, email) and
    Profile (bio, location, birth_date) in a single form submission.
    """
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Profile
        fields = ('bio', 'location', 'birth_date')
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'A short bio about yourself…',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, Country',
            }),
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate User fields from the related User instance
        if self.instance and hasattr(self.instance, 'user'):
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        current_user_pk = self.instance.user.pk
        if User.objects.filter(email__iexact=email).exclude(pk=current_user_pk).exists():
            raise forms.ValidationError(
                'This email address is already in use by another account.'
            )
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Persist User-level fields alongside the Profile
            user = profile.user
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            user.email = self.cleaned_data.get('email', '')
            user.save()
            profile.save()
        return profile
