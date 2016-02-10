from django.forms import ModelForm
from .models import OSFUser


class OSFUserForm(ModelForm):
    class Meta:
        model = OSFUser
        fields = ['osf_id', 'notes']
