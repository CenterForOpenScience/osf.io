from django import forms

from osf.models import PreprintService


class ChangeProviderForm(forms.ModelForm):
    class Meta:
        model = PreprintService
        fields = ('provider',)
