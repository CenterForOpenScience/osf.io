from past.builtins import basestring
from datetime import datetime

from django import forms
from django.core.validators import validate_email

from framework.auth.core import get_user
from osf.models import Conference
from website.conferences.exceptions import ConferenceError


class MultiEmailField(forms.Field):

    def prepare_value(self, value):
        if not value:
            ret = None
        else:
            if isinstance(value, basestring):
                ret = value
            else:
                ret = ', '.join(list(value))
        return ret

    def to_python(self, value):
        if not value:
            return []
        return [r.strip().lower() for r in value.split(',')]

    def validate(self, value):
        super(MultiEmailField, self).validate(value)
        for email in value:
            validate_email(email)


class MeetingForm(forms.Form):
    # Value to tell if this is being created or is an edit
    edit = forms.BooleanField(
        label='edit',
        initial=False,
        required=False,
        widget=forms.HiddenInput(),
    )
    endpoint = forms.CharField(
        label='Endpoint (Unique, short id)',
        required=True,
    )
    name = forms.CharField(
        label='Conference name',
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}),
    )
    info_url = forms.URLField(
        label='Info url',
        required=False
    )
    homepage_link_text = forms.CharField(
        label='Homepage link text (Default: "Conference homepage")',
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
    )
    location = forms.CharField(
        label='Location',
        required=False,
    )
    start_date = forms.DateField(
        required=False,
        label='Start date (e.g. Nov 7 2016 or 11/7/2016)'
    )
    end_date = forms.DateField(
        required=False,
        label='End date (e.g. Nov 9 2016 or 11/9/2016)'
    )
    logo_url = forms.URLField(
        label='Logo url',
        required=False,
        widget=forms.TextInput(attrs={'size': '60'}),
    )
    is_meeting = forms.BooleanField(
        label='This is a meeting',
        initial=True,
        required=False,
    )
    active = forms.BooleanField(
        label='Conference is active',
        required=False,
        initial=True,
    )
    admins = MultiEmailField(
        label='Conference administrator emails (comma separated)',
        widget=forms.TextInput(attrs={'size': '50'}),
        required=False,
    )
    public_projects = forms.BooleanField(
        label='Projects are public',
        required=False,
        initial=True,
    )
    poster = forms.BooleanField(
        label='Posters',
        required=False,
        initial=True,
    )
    talk = forms.BooleanField(
        label='Talks',
        required=False,
        initial=True,
    )
    submission1 = forms.CharField(
        label='Name for Submission 1 (poster)'
    )
    submission2 = forms.CharField(
        label='Name for Submission 2 (talk)'
    )
    submission1_plural = forms.CharField(
        label='Plural for submission 1'
    )
    submission2_plural = forms.CharField(
        label='Plural for submission 2'
    )
    meeting_title_type = forms.CharField(
        label='Title for the type of meeting'
    )
    add_submission = forms.CharField(
        label='Add submission'
    )
    mail_subject = forms.CharField(
        label='Mail subject'
    )
    mail_message_body = forms.CharField(
        label='Message body for mail',
        widget=forms.TextInput(attrs={'size': '60'}),
    )
    mail_attachment = forms.CharField(
        label='Mail attachment message',
        widget=forms.TextInput(attrs={'size': '60'}),
    )
    auto_check_spam = forms.BooleanField(
        label='Automatically check spam?',
        required=False,
    )

    def clean_start_date(self):
        date = self.cleaned_data.get('start_date')
        if date is not None:
            return datetime.combine(date, datetime.min.time())

    def clean_end_date(self):
        date = self.cleaned_data.get('end_date')
        if date is not None:
            return datetime.combine(date, datetime.min.time())

    def clean_endpoint(self):
        endpoint = self.cleaned_data['endpoint']
        edit = self.cleaned_data['edit']
        try:
            Conference.get_by_endpoint(endpoint, False)
            if not edit:
                raise forms.ValidationError(
                    'A meeting with this endpoint exists already.'
                )
        except ConferenceError:
            if edit:
                raise forms.ValidationError(
                    'Meeting not found with this endpoint to update'
                )
        return endpoint

    def clean_admins(self):
        emails = self.cleaned_data['admins']
        for email in emails:
            user = get_user(email=email)
            if not user or user is None:
                raise forms.ValidationError(
                    '{} does not have an OSF account'.format(email)
                )
        return emails
