from django.forms import ModelForm
from .models import Conference, ConferenceFieldNames


class ConferenceFieldNamesForm(ModelForm):
    class Meta:
            model = ConferenceFieldNames
            fields = ['submission1', 'submission2', 'submission1_plural', 'submission2_plural',
            'meeting_title_type', 'add_submission', 'mail_subject', 'mail_message_body', 'mail_attachment', ]
    def __init__(self, *args, **kwargs):
        super(ConferenceFieldNamesForm, self).__init__(*args, **kwargs)

class ConferenceForm(ModelForm):
    class Meta:
            model = Conference
            fields = ['endpoint', 'name', 'info_url', 'logo_url', 'active', 'public_projects', 'admins', 'talk', 'num_submissions', ]
    def __init__(self, *args, **kwargs):
        super(ConferenceForm, self).__init__(*args, **kwargs)
