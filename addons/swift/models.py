# -*- coding: utf-8 -*-

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models

from framework.auth.core import Auth
from osf.models.files import File, Folder, BaseFileNode

from addons.base import exceptions

from addons.swift.serializer import SwiftSerializer
from addons.swift.utils import container_exists, get_container_names

from addons.swift.provider import SwiftProvider

class SwiftFileNode(BaseFileNode):
    _provider = 'swift'


class SwiftFolder(SwiftFileNode, Folder):
    pass


class SwiftFile(SwiftFileNode, File):
    version_identifier = 'version'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = SwiftProvider
    serializer = SwiftSerializer


class NodeSettings(BaseStorageAddon, BaseOAuthNodeSettings):
    oauth_provider = SwiftProvider
    serializer = SwiftSerializer

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = SwiftProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_name

    def fetch_folder_name(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        provider = SwiftProvider(self.external_account)
        if not container_exists(provider.auth_url, provider.username,
                                provider.password, provider.tenant_name, folder_id):
            error_message = ('We are having trouble connecting to that container. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)
        self.folder_name = str(folder_id)
        self.save()

        self.nodelogger.log(action='bucket_linked', extra={'bucket': str(folder_id)}, save=True)

    def get_folders(self, **kwargs):
        try:
            containers = get_container_names(self)
        except:
            raise exceptions.InvalidAuthError()

        return [
            {
                'addon': 'swift',
                'kind': 'folder',
                'id': container,
                'name': container,
                'path': container,
                'urls': {
                    'folders': ''
                }
            }
            for container in containers
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
            raise exceptions.AddonError('Cannot serialize credentials for Swift addon')
        provider = SwiftProvider(self.external_account)
        return {
            'auth_url': provider.auth_url,
            'tenant_name': provider.tenant_name,
            'username': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for Swift addon')
        return {
            'container': self.folder_id
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='swift')

        self.owner.add_log(
            'swift_{0}'.format(action),
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
