from django import forms
from osf.models.rdm_announcement import RdmAnnouncement, RdmAnnouncementOption


class PreviewForm(forms.Form):
    title = forms.CharField(max_length=100,
                            required=False,
                            widget=forms.TextInput(attrs={'class': 'form-control'}),
                            label='Title')
    body = forms.CharField(max_length=60000,
                           required=True,
                           widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '4'}),
                           label='Body',)
    announcement_type = forms.ChoiceField(
        choices=[('Email', 'Email'),
                 ('SNS (Twitter)', 'SNS (Twitter)'),
                 ('SNS (Facebook)', 'SNS (Facebook)'),
                 ('Push notification', 'Push notification')],
        widget=forms.RadioSelect,
        label='Type',
        initial='Email',
    )

    #  body length check
    def clean(self):
        cleaned_data = super(PreviewForm, self).clean()
        announcement_type = cleaned_data.get('announcement_type')
        body = cleaned_data.get('body')
        if announcement_type == "SNS (Twitter)" and len(body) > 140:
            raise forms.ValidationError('Body should be at most 140 characters')
        elif announcement_type == "Push notification" and len(body) > 2000:
            raise forms.ValidationError('Body should be at most 2000 characters')
        else:
            return cleaned_data

class SendForm(forms.ModelForm):

    title = forms.CharField(required=False)
    body = forms.CharField(required=True)
    announcement_type = forms.CharField(required=True)

    class Meta:
        model = RdmAnnouncement
        exclude = ['user','date_sent','is_success']

class SettingsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)

        widgets = {
            'twitter_api_key': forms.TextInput(),
            'twitter_api_secret': forms.TextInput(),
            'twitter_access_token': forms.TextInput(),
            'twitter_access_token_secret': forms.TextInput(),
            'facebook_api_key': forms.TextInput(),
            'facebook_api_secret': forms.TextInput(),
            'facebook_access_token': forms.TextInput(),
            'redmine_api_url': forms.TextInput(),
            'redmine_api_key': forms.TextInput(),
        }

        for field_name in self.fields:
            field = self.fields[field_name]
            field.widget = widgets[field_name]
            field.widget.attrs['class'] = 'form-control'
            field.required = False

    class Meta:
        model = RdmAnnouncementOption
        exclude = ['user']
        labels = {'twitter_api_key': 'API Key',
                  'twitter_api_secret': 'API Secret',
                  'twitter_access_token': 'Access Token',
                  'twitter_access_token_secret': 'Access Token Secret',
                  'facebook_api_key': 'API Key',
                  'facebook_api_secret': 'API Secret',
                  'facebook_access_token': 'Access Token',
                  'redmine_api_url': 'API URL',
                  'redmine_api_key': 'API Key',
                  }