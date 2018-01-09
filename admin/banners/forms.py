from django import forms
from osf.models import ScheduledBanner
from django.forms.widgets import TextInput, DateInput


class BannerForm(forms.ModelForm):
    class Meta:
        model = ScheduledBanner
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'class': 'colorpicker'}),
            'start_date': DateInput(attrs={'class': 'datepicker'}),
            'end_date': DateInput(attrs={'class': 'datepicker'}),
            'license': TextInput(),
        }
