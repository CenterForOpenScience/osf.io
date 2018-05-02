from django import forms

from osf.models import Preprint


class ChangeProviderForm(forms.ModelForm):
    class Meta:
        model = Preprint
        fields = ('provider',)
