from django import forms

from osf.models.storage import InstitutionAssetFile
from osf.models.institution import Institution

class InstitutionAssetFileForm(forms.ModelForm):
    class Meta:
        model = InstitutionAssetFile
        fields = ['name', 'file', 'institutions', 'id']

    id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    institutions = forms.ModelMultipleChoiceField(Institution.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False)

    def clean(self):
        cleaned_data = super().clean()
        obj_id = int(cleaned_data.get('id', None) or 0)
        for institution in cleaned_data.get('institutions', []):
            if institution.asset_files.exclude(id=obj_id).filter(name=cleaned_data.get('name', '')).exists():
                raise forms.ValidationError(f'Naming conflict detected on Institution "{institution.name}"')
        return cleaned_data
