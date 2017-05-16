from django import forms
from osf.models import Institution


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'modm_model_path', 'modm_query', 'is_deleted', 'contributors'
        ]
