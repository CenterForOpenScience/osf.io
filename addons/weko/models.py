# -*- coding: utf-8 -*-
from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models

from framework.auth.decorators import Auth

from osf.models.files import File, Folder, BaseFileNode

from addons.weko.serializer import WEKOSerializer
from addons.weko.utils import WEKONodeLogger
from addons.weko.provider import WEKOProvider


class WEKOFileNode(BaseFileNode):
    _provider = 'weko'


class WEKOFolder(WEKOFileNode, Folder):
    pass


class WEKOFile(WEKOFileNode, File):
    version_identifier = 'version'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer

    index_title = models.TextField(blank=True, null=True)
    index_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = WEKOProvider(self.external_account)
        return self._api

    @property
    def folder_name(self):
        return self.index_title

    @property
    def complete(self):
        return bool(self.has_auth and self.index_id is not None)

    @property
    def folder_id(self):
        return self.index_id

    @property
    def folder_path(self):
        pass

    @property
    def nodelogger(self):
        # TODO: Use this for all log actions
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return WEKONodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, index, auth=None):
        self.index_id = index.identifier
        self.index_title = index.title

        self.save()

        if auth:
            self.owner.add_log(
                action='weko_index_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': index.title,
                },
                auth=auth,
            )

    def clear_settings(self):
        """Clear selected index"""
        self.index_id = None
        self.index_title = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='weko_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        provider = WEKOProvider(self.external_account)
        if provider.repoid is not None:
            return {'token': self.external_account.oauth_key,
                    'user_id': provider.userid}
        else:
            return {'password': provider.password,
                    'user_id': provider.userid}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('WEKO is not configured')
        provider = WEKOProvider(self.external_account)
        return {
            'nid': self.owner._id,
            'url': provider.sword_url,
            'index_id': self.index_id,
            'index_title': self.index_title,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='weko')
        self.owner.add_log(
            'weko_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.index_title,
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
