from django import forms

from osf.models import InstitutionEntitlement


class InstitutionEntitlementForm(forms.ModelForm):
    class Meta:
        model = InstitutionEntitlement

        exclude = [
            'modifier_id',
        ]
