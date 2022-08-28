from __future__ import unicode_literals

import logging

from django.db import models

from osf.models import base
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import EncryptedJSONField
from website import settings as website_settings

logger = logging.getLogger(__name__)


class ExportDataLocation(base.BaseModel):
    # PROVIDERS_AVAILABLE = ['s3', 's3compat', 'dropboxbusiness', 'nextcloudinstitutions']
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
        """return addon config"""
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

    def serialize_waterbutler_credentials(self, provider_name):
        storage_credentials = self.waterbutler_credentials["storage"]
        if provider_name == 's3':
            result = {
                'access_key': storage_credentials['access_key'],
                'secret_key': storage_credentials['secret_key'],
            }
        elif provider_name == 's3compat':
            result = {
                'access_key': storage_credentials['access_key'],
                'secret_key': storage_credentials['secret_key'],
                'host': storage_credentials['host'],
            }
        elif provider_name == 'dropboxbusiness':
            result = {
                'token': storage_credentials['fileaccess_token'],
            }
        elif provider_name == 'nextcloudinstitutions':
            external_account = storage_credentials['external_account']
            provider = external_account['provider']
            result = {
                'host': provider['oauth_secret'],
                'username': provider['display_name'],
                'password': provider['oauth_key'],
            }
        return result

    def serialize_waterbutler_settings(self, provider_name):
        storage_settings = self.waterbutler_settings["storage"]
        if provider_name == 's3':
            result = {
                'bucket': storage_settings['bucket'],
                'encrypt_uploads': storage_settings['folder']['encrypt_uploads'],
            }
        elif provider_name == 's3compat':
            result = {
                'bucket': storage_settings['bucket'],
                'encrypt_uploads': storage_settings['folder']['encrypt_uploads'],
            }
        elif provider_name == 'dropboxbusiness':
            result = {
                'folder': '/',
                'admin_dbmid': storage_settings['admin_dbmid'],
                'team_folder_id': storage_settings['team_folder_id'],
            }
        elif provider_name == 'nextcloudinstitutions':
            from addons.nextcloudinstitutions import settings as nci_settings
            from addons.base.institutions_utils import KEYNAME_BASE_FOLDER
            extended = storage_settings['extended']
            result = {
                'folder': extended[KEYNAME_BASE_FOLDER],
                'verify_ssl': nci_settings.USE_SSL
            }
        return result
