from django import forms
from osf.models import Institution


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        
        labels = {
        "last_logged": _("Last logged"),
        "name": _("Name"),
        "description": _("Description"),
        "banner_name": _("Banner name"),
        "logo_name": _("Logo name"),
        "delegation_protocol": "Delegation protocol",
        "login_url": "Login url",
        "logout_url": "Logout url",
        "domains": "Domains",
        "email_domains": "Email domains",
        }

        exclude = [
            'is_deleted', 'contributors'
        ]
