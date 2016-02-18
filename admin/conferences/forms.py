from django.forms import ModelForm
from .models import Conference


class ConferenceForm(ModelForm):
    class Meta:
            model = Conference
            fields = ['name', 'info_url', 'logo_url', 'active', 'public_projects', 'admins', 'talk', ]
    def __init__(self, *args, **kwargs):
        super(ConferenceForm, self).__init__(*args, **kwargs)
