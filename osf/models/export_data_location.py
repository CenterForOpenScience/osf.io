from __future__ import unicode_literals

import logging

from django.db import models

from osf.models import base
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website import settings as website_settings
from website.util import api_v2_url

logger = logging.getLogger(__name__)


class ExportDataLocation(base.BaseModel):
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

    class Meta:
        unique_together = ('institution_guid', 'name')
