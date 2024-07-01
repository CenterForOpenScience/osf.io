from django import forms
from django.core.validators import validate_email


class GuidForm(forms.Form):
    guid = forms.CharField(label='Guid', min_length=5, max_length=10, required=True)


class MultiEmailField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        return [r.strip().lower() for r in value.split(',')]

    def validate(self, value):
        super().validate(value)
        for email in value:
            validate_email(email)


class ImportFileForm(forms.Form):
    file = forms.FileField()


class ArchiveRegistrationWithPigeonForm(forms.Form):
    guid_to_archive = forms.CharField(label='guid_to_archive', min_length=5, max_length=1024, required=False)
