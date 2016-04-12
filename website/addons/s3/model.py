# -*- coding: utf-8 -*-

import markupsafe
from modularodm import fields

from framework.auth.core import Auth

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.s3.provider import S3Provider
from website.addons.s3.serializer import S3Serializer
from website.addons.s3.settings import ENCRYPT_UPLOADS_DEFAULT


class S3UserSettings(AddonOAuthUserSettingsBase):

    oauth_provider = S3Provider
    serializer = S3Serializer


class S3NodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = S3Provider
    serializer = S3Serializer

    bucket = fields.StringField()
    encrypt_uploads = fields.BooleanField(default=ENCRYPT_UPLOADS_DEFAULT)

    @property
    def folder_name(self):
        return self.bucket

    @property
    def folder_id(self):
        return self.bucket

    @property
    def folder_path(self):
        return self.bucket

    def fetch_folder_name(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.bucket)

    def set_folder(self, folder_id, auth):
        self.bucket = str(folder_id)
        self.save()

        self.nodelogger.log(action="bucket_linked", extra={'bucket': str(folder_id)}, save=True)

    @property
    def complete(self):
        return self.has_auth and self.bucket is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=save)

    def clear_settings(self):
        self.bucket = None

    def deauthorize(self, auth=None, log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        if log:
            self.nodelogger.log(action='node_deauthorized', save=True)

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(S3NodeSettings, self).delete(save=save)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Cannot serialize credentials for S3 addon')
        return {
            'access_key': self.external_account.oauth_key,
            'secret_key': self.external_account.oauth_secret,
        }

    def serialize_waterbutler_settings(self):
        if not self.bucket:
            raise exceptions.AddonError('Cannot serialize settings for S3 addon')
        return {
            'bucket': self.bucket,
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
                'bucket': self.bucket,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True)
