from django.db import models
from django.forms import ModelForm


class Institution(models.Model):
    osf_id = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    logo_name = models.CharField(max_length=100)
    description = models.TextField()
    saml = models.CharField(max_length=1000)


class InstitutionForm(ModelForm):
    class Meta:
        model = Institution
        fields = ['osf_id', 'name', 'logo_name', 'description', 'saml']
