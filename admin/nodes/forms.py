from django import forms

from osf.models import Registration
from django.forms.widgets import DateInput


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = [
            'title',
            'description',
            'is_public',
            'node_license',
            'category',
            'provider',
            'registered_schema',
            'registered_meta',
            'registered_date',
            'registered_user',
            'external_registration',
            'registered_from',
            'registration_approval',
            'retraction',
            'embargo',
            'embargo_termination_approval',
            'files_count',
        ]
        widgets = {
            'registered_date': DateInput(attrs={'class': 'datepicker'}),
        }
