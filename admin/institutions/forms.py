from django import forms
from osf.models import Institution


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'is_deleted', 'contributors'
        ]
