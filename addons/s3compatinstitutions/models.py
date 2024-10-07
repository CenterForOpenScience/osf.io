# -*- coding: utf-8 -*-
import logging
import re

from django.db import models

import boto3

from addons.base import exceptions
from addons.base import institutions_utils as inst_utils
from addons.base.institutions_utils import (
    InstitutionsNodeSettings,
    InstitutionsStorageAddon
)
from addons.s3compatinstitutions import settings, apps
from osf.models.external import BasicAuthProviderMixin
from osf.models.files import File, Folder, BaseFileNode
#from osf.utils.permissions import ADMIN, READ, WRITE

logger = logging.getLogger(__name__)

FULL_NAME = apps.FULL_NAME
SHORT_NAME = apps.SHORT_NAME

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_{}: {}'.format(SHORT_NAME, msg))
    else:
        logger.debug(msg)

if not ENABLE_DEBUG:
    logging.getLogger('botocore.vendored.requests.packages.urllib3.connectionpool').setLevel(logging.CRITICAL)

class S3CompatInstitutionsFileNode(BaseFileNode):
    _provider = SHORT_NAME


class S3CompatInstitutionsFolder(S3CompatInstitutionsFileNode, Folder):
    pass


class S3CompatInstitutionsFile(S3CompatInstitutionsFileNode, File):
    pass


class S3CompatInstitutionsProvider(BasicAuthProviderMixin):
    name = FULL_NAME
    short_name = SHORT_NAME


class NodeSettings(InstitutionsNodeSettings, InstitutionsStorageAddon):
    FULL_NAME = FULL_NAME
    SHORT_NAME = SHORT_NAME

    folder_id = models.TextField(blank=True, null=True)

    @classmethod
    def addon_settings(cls):
        return settings

    @classmethod
    def get_provider(cls, external_account):
        return S3CompatInstitutionsProvider(external_account)

    @classmethod
    def get_debug_provider(cls):
        if not (settings.DEBUG_URL
                and settings.DEBUG_USER
                and settings.DEBUG_PASSWORD):
            return None

        class DebugProvider(object):
            host = settings.DEBUG_URL
            username = settings.DEBUG_USER
            password = settings.DEBUG_PASSWORD
        return DebugProvider()

    @classmethod
    def get_client(cls, provider):
        port = 443
        scheme = 'https'
        m = re.match(r'^(.+)\:([0-9]+)$', provider.host)
        if m is not None:
            # host = m.group(1)
            port = int(m.group(2))
            if port != 443:
                scheme = 'http'
        client = boto3.client('s3',
            aws_access_key_id=provider.username,
            aws_secret_access_key=provider.password,
            endpoint_url='{}://{}'.format(scheme, provider.host))
        return client

    @classmethod
    def _list_count(cls, client, bucket, key):
        # may raise
        res = client.list_objects(Bucket=bucket, Prefix=key)
        contents = res.get('Contents')
        if not contents:
            return 0
        return len(contents)

    @classmethod
    def can_access(cls, client, bucket):
        # access check
        cls._list_count(client, bucket, '/')  # may raise

    @classmethod
    def create_folder(cls, client, base_folder, name):
        bucket = base_folder
        key = name.strip('/') + '/'
        logger.info(u'create folder: bucket={}, key={}'.format(bucket, key))
        client.put_object(Bucket=bucket, Key=key)  # may raise

    @classmethod
    def remove_folder(cls, client, base_folder, name):
        bucket = base_folder
        key = name.strip('/') + '/'
        count = cls._list_count(client, bucket, key)
        if count != 0:
            raise exceptions.AddonError(u'cannot remove folder (not empty): bucket={}, key={}'.format(bucket, key))
        logger.info(u'remove folder: bucket={}, key={}'.format(bucket, key))
        client.delete_object(Bucket=bucket, Key=key)  # may raise

    @classmethod
    def rename_folder(cls, client, base_folder, old_name, new_name):
        logger.info(u'rename operation is not supported in s3compatinstitutions')

    @classmethod
    def root_folder_format(cls):
        # DO NOT USE "{title}", see sync_title()
        return settings.ROOT_FOLDER_FORMAT

    @property
    def exists(self):
        try:
            self._list_count(self.client, self.bucket, self.root_prefix)
            return True
        except Exception:
            return False

    # override
    def sync_title(self):
        # not supported
        # S3 and S3 compat cannot rename buckets and folders.
        pass

    def sync_contributors(self):
        # not supported [GRDM-20960]
        pass

    @property
    def bucket(self):
        return self.base_folder

    @property
    def root_prefix(self):
        return self.folder_name

    def serialize_waterbutler_credentials_impl(self):
        return {
            'host': self.provider.host,
            'access_key': self.provider.username,
            'secret_key': self.provider.password,
        }

    def serialize_waterbutler_settings(self):
        return {
            'nid': self.owner._id,
            'bucket': self.bucket,
            'prefix': self.root_prefix,
            'encrypt_uploads': settings.ENCRYPT_UPLOADS
        }

    def copy_folders(self, dest_addon):
        c = self.client
        destc = dest_addon.client
        res = c.list_objects(Bucket=self.bucket, Prefix=self.root_prefix,
                             MaxKeys=1000)  # may raise
        contents = res.get('Contents')
        # logger.debug(u'Contents: {}'.format(contents))
        if not contents:
            return
        for item in contents:
            key = item.get('Key')
            if not key:
                continue
            parts = key.split('/')
            if len(parts) <= 1:
                continue
            if parts[0] != self.root_prefix:
                continue
            # A/B/C/ -> B/C/
            # A/B/C/file -> B/C/
            key = '/'.join(parts[1:-1]) + '/'
            if key == '/':
                continue
            key = dest_addon.root_prefix + '/' + key
            logger.debug(u'copy_folders: put_object({})'.format(key))
            destc.put_object(Bucket=dest_addon.bucket, Key=key)  # may raise


inst_utils.register(NodeSettings)
