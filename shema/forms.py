from django import forms
from .models import Profile


class BioForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'maxlength': 500}),
        }
