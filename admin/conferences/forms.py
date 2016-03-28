from django import forms

class ConferenceForm(forms.Form):
    name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Required'}))
    endpoint = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Required'}))
    info_url = forms.CharField(required=False)
    logo_url = forms.CharField(required=False)
    active = forms.BooleanField(required=False, initial=True)
    public_projects = forms.BooleanField(required=False, initial=True)
    poster = forms.BooleanField(required=False, initial=True)
    talk = forms.BooleanField(required=False, initial=True)

class ConferenceFieldNamesForm(forms.Form):
    submission1 = forms.CharField(required=False)
    submission2 = forms.CharField(required=False)
    submission1_plural = forms.CharField(required=False)
    submission2_plural = forms.CharField(required=False)
    meeting_title_type = forms.CharField(required=False)
    add_submission = forms.CharField(required=False)
    mail_subject = forms.CharField(required=False)
    mail_message_body = forms.CharField(required=False)
    mail_attachment = forms.CharField(required=False)
