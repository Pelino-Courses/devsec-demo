from django import forms
from .models import Profile


class BioForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }


class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['document']
