from django import forms
from osf.exceptions import ValidationValueError
from django.forms.widgets import TextInput, DateInput
from osf.models.banner import ScheduledBanner, validate_banner_dates


ACCEPTABLE_FILE_TYPES = ('svg',)

class BannerForm(forms.ModelForm):
    class Meta:
        model = ScheduledBanner
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'class': 'colorpicker'}),
            'start_date': DateInput(attrs={'class': 'datepicker'}),
            'end_date': DateInput(attrs={'class': 'datepicker'}),
            'default_alt_text': TextInput(attrs={'placeholder': 'Alt text for accessibility'}),
            'mobile_alt_text': TextInput(attrs={'placeholder': 'Alt text for accessibility'}),
        }
        labels = {
            'default_alt_text': 'Default photo alt text',
            'mobile_alt_text': 'Mobile photo alt text'
        }

    def __init__(self, *args, **kwargs):
        banner = kwargs.get('instance')
        self.banner_id = banner.id if banner else None
        super(BannerForm, self).__init__(*args, **kwargs)

    def clean_default_photo(self):
        return self.check_photo_type(self.cleaned_data['default_photo'])

    def clean_mobile_photo(self):
        return self.check_photo_type(self.cleaned_data['mobile_photo'])

    def check_photo_type(self, photo):
        if not photo.name.lower().endswith(ACCEPTABLE_FILE_TYPES):
            raise forms.ValidationError('Photos must be of type {}.'.format(ACCEPTABLE_FILE_TYPES))
        return photo

    def clean(self):
        data = self.cleaned_data

        try:
            validate_banner_dates(self.banner_id, data['start_date'], data['end_date'])
        except ValidationValueError as e:
            raise forms.ValidationError(e.message)

        return data
