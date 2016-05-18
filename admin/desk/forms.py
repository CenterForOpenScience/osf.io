from django import forms

from admin.base.forms import MultiEmailField


class CaseForm(forms.Form):
    subject = forms.CharField(
        label='Case subject'
    )
    priority = forms.IntegerField(
        label='Priority 1 to 10'
    )
    labels = forms.CharField(
        label='Desk labels'
    )  # comma separated list
    message_from = forms.CharField(
        label='Customer email'
    )
    body = forms.CharField(
        widget=forms.Textarea,
        label='Description'
    )
    created_at = forms.DateField(
        label='Date'
    )


class CustomerForm(forms.Form):
    first_name = forms.CharField(
        label='First name'
    )
    last_name = forms.CharField(
        label='Last name'
    )
    emails = MultiEmailField(
        label='Comma separated emails'
    )
