from django import forms
from osf.models import Institution
from django.utils.translation import ugettext_lazy as _


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution

        labels = {
            'last_logged': _('Last logged'),
            'name': _('Name'),
            'description': _('Description'),
            'banner_name': _('Banner name'),
            'logo_name': _('Logo name'),
            'delegation_protocol': _('Delegation protocol'),
            'login_url': _('Login url'),
            'logout_url': _('Logout url'),
            'domains': _('Domains'),
            'email_domains': _('Email domains'),
        }

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
