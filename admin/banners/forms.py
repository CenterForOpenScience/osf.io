from django import forms
from osf.models import ScheduledBanner
from django.forms.widgets import TextInput


class BannerForm(forms.ModelForm):
    class Meta:
        model = ScheduledBanner
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'class': 'colorpicker'}),
            'start_date': forms.DateInput(attrs={'class': 'datepicker'}),
            'end_date': forms.DateInput(attrs={'class': 'datepicker'}),
            'license': TextInput(),
        }
