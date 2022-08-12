from __future__ import unicode_literals

import logging

from django.apps import apps
from django.db import models
from django_extensions.db.models import TimeStampedModel

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website import settings as website_settings
from website.util import api_v2_url

settings = apps.get_app_config('addons_osfstorage')

logger = logging.getLogger(__name__)


class ExportDataLocation(TimeStampedModel):
    institution_guid = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255)
    waterbutler_credentials = EncryptedJSONField(default=dict)
    waterbutler_url = models.URLField(default=website_settings.WATERBUTLER_URL)
    mfr_url = models.URLField(default=website_settings.MFR_SERVER_URL)
    waterbutler_settings = DateTimeAwareJSONField(default=dict)

    def __repr__(self):
        return f'"({self.institution_guid}){self.name}"'

    __str__ = __repr__

    def __unicode__(self):
        return '{}'.format(self.name)

    def get_absolute_url(self):
        return '{}export_locations/{}'.format(self.absolute_api_v2_url, self.institution_guid)

    @property
    def absolute_api_v2_url(self):
        path = '/export_locations/{}/'.format(self.institution_guid)
        return api_v2_url(path)

    class Meta:
        unique_together = ('institution_guid', 'name')
