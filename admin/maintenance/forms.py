from django import forms
from osf.models import MaintenanceState
from django.utils.translation import ugettext_lazy as _


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceState
        labels = {
            'level': _('Level'),
        }
        fields = ['level']
