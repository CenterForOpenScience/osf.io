# -*- coding: utf-8 -*-

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth.core import Auth
from osf.models.files import File, Folder, BaseFileNode
from addons.base import exceptions
from addons.s3compat.provider import S3CompatProvider
from addons.s3compat.serializer import S3CompatSerializer
from addons.s3compat.settings import ENCRYPT_UPLOADS_DEFAULT
from addons.s3compat.utils import (bucket_exists,
                                     get_bucket_location_or_error,
                                     get_bucket_names,
                                     find_service_by_host)

class S3CompatFileNode(BaseFileNode):
    _provider = 's3compat'


class S3CompatFolder(S3CompatFileNode, Folder):
    pass


class S3CompatFile(S3CompatFileNode, File):
    version_identifier = 'version'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = S3CompatProvider
    serializer = S3CompatSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = S3CompatProvider
    serializer = S3CompatSerializer

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    folder_location = models.TextField(blank=True, null=True)
    encrypt_uploads = models.BooleanField(default=ENCRYPT_UPLOADS_DEFAULT)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_path(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        if not bucket_exists(self.external_account.provider_id.split('\t')[0],
                             self.external_account.oauth_key,
                             self.external_account.oauth_secret, folder_id):
            error_message = ('We are having trouble connecting to that bucket. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)
        host = self.external_account.provider_id.split('\t')[0]

        bucket_location = get_bucket_location_or_error(
            host,
            self.external_account.oauth_key,
            self.external_account.oauth_secret,
            folder_id
        )
        self.folder_location = bucket_location
        try:
            service = find_service_by_host(host)
            bucket_location = service['bucketLocations'][bucket_location]['name']
        except KeyError:
            # Unlisted location, Default to the key.
            pass
        if bucket_location is None or bucket_location == '':
            bucket_location = 'Default'

        self.folder_name = '{} ({})'.format(folder_id, bucket_location)
        self.save()

        self.nodelogger.log(action='bucket_linked', extra={'bucket': str(folder_id)}, save=True)

    def get_folders(self, **kwargs):
        # This really gets only buckets, not subfolders,
        # as that's all we want to be linkable on a node.
        try:
            buckets = get_bucket_names(self)
        except Exception:
            raise exceptions.InvalidAuthError()

        return [
            {
                'addon': 's3compat',
                'kind': 'folder',
                'id': bucket,
                'name': bucket,
                'path': bucket,
                'urls': {
                    'folders': ''
                }
            }
            for bucket in buckets
        ]

    @property
    def complete(self):
        return self.has_auth and self.folder_id is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=save)

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None
        self.folder_location = None

    def deauthorize(self, auth=None, log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        if log:
            self.nodelogger.log(action='node_deauthorized', save=True)

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(NodeSettings, self).delete(save=save)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Cannot serialize credentials for S3 Compatible Storage addon')
        host = self.external_account.provider_id.split('\t')[0]
        if self.folder_location is not None and len(self.folder_location) > 0:
            try:
                service = find_service_by_host(host)
                host = service['bucketLocations'][self.folder_location]['host']
            except KeyError:
                # Unlisted location, use default host
                pass
        return {
            'host': host,
            'access_key': self.external_account.oauth_key,
            'secret_key': self.external_account.oauth_secret,
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for S3 Compatible Storage addon')
        return {
            'bucket': self.folder_id,
            'encrypt_uploads': self.encrypt_uploads
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='s3compat')

        self.owner.add_log(
            's3compat_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'bucket': self.folder_id,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), log=True)
