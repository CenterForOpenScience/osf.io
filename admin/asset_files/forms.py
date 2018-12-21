from django import forms

from osf.models.storage import ProviderAssetFile
from osf.models.provider import AbstractProvider


class ProviderAssetFileForm(forms.ModelForm):
    class Meta:
        model = ProviderAssetFile
        fields = ['name', 'file', 'providers', 'id']

    id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    providers = forms.ModelMultipleChoiceField(AbstractProvider.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False)

    def clean(self):
        cleaned_data = super(ProviderAssetFileForm, self).clean()
        obj_id = int(cleaned_data.get('id', None) or 0)
        for provider in cleaned_data.get('providers', []):
            if provider.asset_files.exclude(id=obj_id).filter(name=cleaned_data.get('name', '')).exists():
                raise forms.ValidationError('Naming conflict detected on Provider "{}"'.format(provider.name))
        return cleaned_data
