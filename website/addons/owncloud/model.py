# -*- coding: utf-8 -*-
from urllib2 import HTTPError
import logging
from modularodm import fields
from framework.auth import Auth
from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase,
)
from website.addons.owncloud.serializer import OwnCloudSerializer
from website.addons.owncloud.utils import (
    ExternalAccountConverter, OwnCloudNodeLogger
)

logger = logging.getLogger(__name__)

class OwnCloudProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'ownCloud'
    short_name = 'owncloud'
    serializer = OwnCloudSerializer

    def __init__(self, account=None):
        super(OwnCloudProvider, self).__init__()
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

class AddonOwnCloudUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = OwnCloudProvider
    serializer = OwnCloudSerializer

class AddonOwnCloudNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = OwnCloudProvider
    serializer = OwnCloudSerializer

    folder_name = fields.StringField()

    @property
    def complete(self):
        return bool(self.has_auth and self.folder_name is not None)

    @property
    def folder_id(self):
        return self.folder_name

    @property
    def folder_path(self):
        return self.folder_name

    @property
    def nodelogger(self):
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return OwnCloudNodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, folder, auth=None):
        if folder == '/ (Full ownCloud)':
            folder = '/'
        self.folder_name = folder
        self.save()
        if auth:
            self.owner.add_log(
                action='owncloud_folder_selected',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'folder': folder,
                },
                auth=auth,
            )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        try:
            return super(AddonOwnCloudNodeSettings, self)._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError:
            return []

    def clear_settings(self):
        self.folder_name = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='owncloud_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        converted = ExternalAccountConverter(account=self.external_account)
        return {'host': converted.host,
                'username': converted.username,
                'password': converted.password
                }

    def serialize_waterbutler_settings(self):
        if not self.folder_name:
            raise exceptions.AddonError('ownCloud is not configured')
        return {'folder': self.folder_name}

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='owncloud')
        self.owner.add_log(
            'owncloud_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_name,
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    ##### Callback overrides #####

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
