from django import forms


class CaseForm(forms.Form):
    subject = forms.CharField()
    priority = forms.IntegerField()
    labels = forms.CharField()  # comma separated list
    message_from = forms.CharField()
    body = forms.CharField(widget=forms.Textarea)
    created_at = forms.DateField()


class CustomerForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    emails = forms.CharField()
