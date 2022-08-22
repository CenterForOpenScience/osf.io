from __future__ import unicode_literals

import logging

from django.db import models

from osf.models import base
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website import settings as website_settings

logger = logging.getLogger(__name__)


class ExportDataLocation(base.BaseModel):
    institution_guid = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255)
    waterbutler_credentials = EncryptedJSONField(default=dict)
    waterbutler_url = models.URLField(default=website_settings.WATERBUTLER_URL)
    mfr_url = models.URLField(default=website_settings.MFR_SERVER_URL)
    waterbutler_settings = DateTimeAwareJSONField(default=dict)

    class Meta:
        unique_together = ('institution_guid', 'name')
        ordering = ['pk']

    def __repr__(self):
        return f'"{self.institution_guid}/{self.name}"'

    __str__ = __repr__

    def __unicode__(self):
        return '{}'.format(self.name)

    @property
    def provider_name(self):
        waterbutler_settings = self.waterbutler_settings
        provider_name = None
        if "storage" in waterbutler_settings:
            storage = waterbutler_settings["storage"]
            if "provider" in storage:
                provider_name = storage["provider"]

        return provider_name

    @property
    def addon(self):
        for addon in website_settings.ADDONS_AVAILABLE:
            if addon.short_name == self.provider_name:
                return addon
        return None

    @property
    def provider_short_name(self):
        if hasattr(self.addon, 'short_name'):
            return self.addon.short_name
        return None

    @property
    def provider_full_name(self):
        if hasattr(self.addon, 'full_name'):
            return self.addon.full_name
        return None
