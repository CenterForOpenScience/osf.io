from django import forms
from osf.models.institution import Institution, SSOAvailability


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'is_deleted', 'contributors', 'storage_regions',
        ]

    def clean(self):
        super().clean()

        if hasattr(self, 'cleaned_data') and self.changed_data:
            if not self.cleaned_data['delegation_protocol']:
                if self.cleaned_data['sso_availability'] != SSOAvailability.UNAVAILABLE.value:
                    self.add_error('sso_availability', 'Must be UNAVAILABLE when no protocol')

            elif self.cleaned_data['deactivated']:
                if self.cleaned_data['sso_availability'] != SSOAvailability.HIDDEN.value:
                    self.add_error('sso_availability', 'Inactive must be HIDDEN')


class InstitutionalMetricsAdminRegisterForm(forms.Form):
    """ A form that finds an existing OSF User, and grants permissions to that
    user so that they can view institutional metrics"""

    def __init__(self, *args, **kwargs):
        kwargs.pop('institution_id')
        super().__init__(*args, **kwargs)

    user_id = forms.CharField(required=True, max_length=5, min_length=5)
