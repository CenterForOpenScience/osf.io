from django import forms

from osf.models.storage import ProviderAssetFile
from osf.models.provider import AbstractProvider


class ProviderAssetFileForm(forms.ModelForm):
    class Meta:
        model = ProviderAssetFile
        fields = ['name', 'file', 'providers']

    providers = forms.ModelMultipleChoiceField(AbstractProvider.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False)
