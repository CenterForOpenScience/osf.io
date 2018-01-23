from django import forms
from osf.models import MaintenanceState


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceState
        fields = ['level']
