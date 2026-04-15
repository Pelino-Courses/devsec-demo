from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import UserProfile


class CustomUserCreationForm(UserCreationForm):
    """
    Extended user registration form with additional profile fields.
    
    Security features:
    - Uses Django's built-in password hashing
    - Validates password strength
    - Prevents common password choices
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        }),
        help_text=_('Required. Enter a valid email address.')
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    student_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student ID'
        }),
        help_text=_('Required. Your unique student identifier.')
    )
    
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        }),
        help_text=_('Password must be at least 8 characters long.')
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap styling to all fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
    
    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                _('This email address is already registered.'),
                code='email_exists'
            )
        return email
    
    def clean_student_id(self):
        """Validate that student_id is unique."""
        student_id = self.cleaned_data.get('student_id')
        if UserProfile.objects.filter(student_id=student_id).exists():
            raise ValidationError(
                _('This student ID is already registered.'),
                code='student_id_exists'
            )
        return student_id
    
    def clean_password2(self):
        """Validate password confirmation matches."""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError(
                _('Passwords do not match.'),
                code='password_mismatch'
            )
        return password2
    
    def save(self, commit=True):
        """
        Save user and create associated UserProfile.
        """
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create the associated UserProfile
            UserProfile.objects.create(
                user=user,
                student_id=self.cleaned_data['student_id']
            )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom login form with improved UX and security labels.
    
    Security features:
    - Uses Django's authentication backend
    - Prevents username enumeration where possible
    """
    
    username = forms.CharField(
        label=_("Username or Email"),
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean_username(self):
        """Allow login by username or email."""
        username = self.cleaned_data.get('username')
        # Try to find user by email if not found by username
        if username and not User.objects.filter(username=username).exists():
            # Check if it's an email and try to get user by email
            if '@' in username:
                try:
                    user = User.objects.get(email=username)
                    username = user.username
                except User.DoesNotExist:
                    pass
        return username


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with improved UX.
    
    Security features:
    - Requires current password verification
    - Uses Django's password validation
    - Enforces password strength requirements
    """
    
    old_password = forms.CharField(
        label=_("Current Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password',
            'autofocus': True
        })
    )
    new_password1 = forms.CharField(
        label=_("New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password'
        }),
        help_text=_('Password must be at least 8 characters long and not entirely numeric.')
    )
    new_password2 = forms.CharField(
        label=_("Confirm New Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )


class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile information.
    """
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ('student_id', 'phone_number', 'bio', 'date_of_birth')
        widgets = {
            'student_id': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # Make student_id read-only
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate first_name and last_name from the related User object
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def clean_email(self):
        """Validate email uniqueness (excluding current user)."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(id=self.instance.user.id).exists():
            raise ValidationError(
                _('This email address is already in use.'),
                code='email_exists'
            )
        return email
    
    def save(self, commit=True):
        """Save profile and update related User object."""
        profile = super().save(commit=False)
        if profile.user:
            profile.user.first_name = self.cleaned_data.get('first_name', '')
            profile.user.last_name = self.cleaned_data.get('last_name', '')
            profile.user.email = self.cleaned_data.get('email', '')
            if commit:
                profile.user.save()
        if commit:
            profile.save()
        return profile
