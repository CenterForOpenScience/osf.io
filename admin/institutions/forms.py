from django import forms
from osf.models import Institution


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'modm_model_path', 'modm_query', '_id', 'is_deleted',
            'contributors', 'logo_name', 'banner_name'
        ]


class ImportFileForm(forms.Form):
    file = forms.FileField()
