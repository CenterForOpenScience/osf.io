from django import forms
from django.core.validators import validate_email


class GuidForm(forms.Form):
    guid = forms.CharField(label='Guid', min_length=5, max_length=5,
                           required=True)  # TODO: Move max to 6 when needed


class MultiEmailField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        return [r.strip().lower() for r in value.split(',')]

    def validate(self, value):
        super(MultiEmailField, self).validate(value)
        for email in value:
            validate_email(email)
