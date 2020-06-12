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
        "delegation_protocol": _("Delegation protocol"),
        "login_url": _("Login url"),
        "logout_url": _("Logout url"),
        "domains": _("Domains"),
        "email_domains": _("Email domains"),
        }

        exclude = [
            'is_deleted', 'contributors'
        ]
