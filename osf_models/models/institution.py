from django.contrib.postgres import fields
from django.db import models
from django.conf import settings

from osf_models.models import base
from osf_models.models.contributor import InstitutionalContributor
from osf_models.models.mixins import Loggable


class Institution(Loggable, base.GuidMixin, base.BaseModel):
    auth_url = models.URLField()
    banner_name = models.CharField(max_length=255)
    contributors = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                          through=InstitutionalContributor,
                                          related_name='institutions')
    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True)
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True)
    logo_name = models.CharField(max_length=255)  # TODO: Could this be a FilePathField?
    logout_url = models.URLField()
    name = models.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(Institution, self).__init__(*args, **kwargs)
