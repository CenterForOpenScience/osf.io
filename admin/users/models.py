from django.db import models
from django.forms import ModelForm


class OSFUser(models.Model):
    osf_id = models.CharField(max_length=5, unique=True)
    notes = models.TextField(verbose_name='Notes for OSF user')


class OSFUserForm(ModelForm):
    class Meta:
        model = OSFUser
        fields = ['notes']
