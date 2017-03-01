from django.forms import ModelForm

from osf.models import Institution


class InstitutionForm(ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'modm_model_path', 'modm_query', '_id', 'is_deleted',
            'contributors', 'logo_name', 'banner_name'
        ]
