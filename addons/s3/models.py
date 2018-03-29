# -*- coding: utf-8 -*-

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth.core import Auth
from osf.models.files import File, Folder, BaseFileNode
from addons.base import exceptions
from addons.s3.provider import S3Provider
from addons.s3.serializer import S3Serializer
from addons.s3.settings import (BUCKET_LOCATIONS,
                                        ENCRYPT_UPLOADS_DEFAULT)
from addons.s3.utils import (bucket_exists,
                                     get_bucket_location_or_error,
                                     get_bucket_names)

class S3FileNode(BaseFileNode):
    _provider = 's3'


class S3Folder(S3FileNode, Folder):
    pass


class S3File(S3FileNode, File):
    version_identifier = 'version'

    @property
    def _hashes(self):
        try:
            return self._history[-1]['extra']['hashes']
        except (IndexError, KeyError):
            return None


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = S3Provider
    serializer = S3Serializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = S3Provider
    serializer = S3Serializer

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    encrypt_uploads = models.BooleanField(default=ENCRYPT_UPLOADS_DEFAULT)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_path(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        if not bucket_exists(self.external_account.oauth_key, self.external_account.oauth_secret, folder_id):
            error_message = ('We are having trouble connecting to that bucket. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)

        bucket_location = get_bucket_location_or_error(
            self.external_account.oauth_key,
            self.external_account.oauth_secret,
            folder_id
        )
        try:
            bucket_location = BUCKET_LOCATIONS[bucket_location]
        except KeyError:
            # Unlisted location, S3 may have added it recently.
            # Default to the key. When hit, add mapping to settings
            pass

        self.folder_name = '{} ({})'.format(folder_id, bucket_location)
        self.save()

        self.nodelogger.log(action='bucket_linked', extra={'bucket': str(folder_id)}, save=True)

    def get_folders(self, **kwargs):
        # This really gets only buckets, not subfolders,
        # as that's all we want to be linkable on a node.
        try:
            buckets = get_bucket_names(self)
        except:
            raise exceptions.InvalidAuthError()

        return [
            {
                'addon': 's3',
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
            raise exceptions.AddonError('Cannot serialize credentials for S3 addon')
        return {
            'access_key': self.external_account.oauth_key,
            'secret_key': self.external_account.oauth_secret,
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for S3 addon')
        return {
            'bucket': self.folder_id,
            'encrypt_uploads': self.encrypt_uploads
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='s3')

        self.owner.add_log(
            's3_{0}'.format(action),
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

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True)
