from django import forms
from osf.exceptions import ValidationValueError
from django.forms.widgets import TextInput, DateInput
from osf.models.banner import ScheduledBanner, validate_banner_dates


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

    def __init__(self, *args, **kwargs):
        banner = kwargs.get('instance')
        self.banner_id = banner.id if banner else None
        super(BannerForm, self).__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data

        try:
            validate_banner_dates(self.banner_id, data['start_date'], data['end_date'])
        except ValidationValueError as e:
            raise forms.ValidationError(e.message)

        return data
