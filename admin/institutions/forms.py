from django import forms
from osf.models import Institution


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        exclude = [
            'is_deleted', 'contributors'
        ]

class InstitutionalMetricsAdminRegisterForm(forms.Form):
    """ A form that finds an existing OSF User, and grants permissions to that
    user so that they can view institutional metrics"""

    def __init__(self, *args, **kwargs):
        kwargs.pop('institution_id')
        super(InstitutionalMetricsAdminRegisterForm, self).__init__(*args, **kwargs)

    user_id = forms.CharField(required=True, max_length=5, min_length=5)
