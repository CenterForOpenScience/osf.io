from django import forms
from django.core.validators import validate_email

from modularodm import Q
from website.models import Conference


class MeetingForm(forms.Form):
    # Value to tell if this is being created or is an edit
    edit = forms.BooleanField(
        required=True,
        initial=False,
    )
    endpoint = forms.CharField(
        label='Endpoint (Unique, short id)',
        required=True,
    )
    name = forms.CharField(
        label='Conference name',
        required=True,
    )
    info_url = forms.CharField(
        label='Info url',
        required=True,
    )
    logo_url = forms.CharField(
        label='Logo url',
    )
    active = forms.BooleanField(
        label='Conference is active',
        required=True,
        initial=True,
    )
    admins = MultiEmailField(
        label='Conference administrator emails (comma separated)',
        widget=forms.CharField
    )
    public_projects = forms.BooleanField(
        label='Projects are public',
        required=True,
        initial=True,
    )
    poster = forms.BooleanField(
        label='Posters',
        required=True,
        initial=True,
    )
    talk = forms.BooleanField(
        label='Talks',
        required=True,
        initial=True,
    )

    def clean_endpoint(self):
        data = self.cleaned_data['endpoint']
        edit = self.cleaned_data['edit']
        if not edit:
            if Conference.find(Q('endpoint', 'eq', data)).count() > 0:
                raise forms.ValidationError(
                    'A meeting with this endpoint exists already.'
                )
        return data


class MultiEmailField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        return [r.strip() for r in value.split(',')]

    def validate(self, value):
        super(MultiEmailField, self).validate(value)
        for email in value:
            validate_email(email)
