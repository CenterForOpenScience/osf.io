# -*- coding: utf-8 -*-
import httplib as http

from modularodm import fields

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError

from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase, exceptions,
)
from website.addons.base import StorageAddonBase

from website.addons.dmptool.client import connect_from_settings_or_401
from website.addons.dmptool.serializer import DmptoolSerializer
from website.addons.dmptool.utils import DmptoolNodeLogger


class DmptoolProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Dmptool'
    short_name = 'dmptool'
    serializer = DmptoolSerializer

    def __init__(self, account=None):
        super(DmptoolProvider, self).__init__()
        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

class AddonDmptoolUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer

class AddonDmptoolNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = DmptoolProvider
    serializer = DmptoolSerializer

    dmptool_alias = fields.StringField()
    dmptool = fields.StringField()
    dataset_doi = fields.StringField()
    _dataset_id = fields.StringField()
    dataset = fields.StringField()

    @property
    def folder_name(self):
        return self.dataset

    @property
    def dataset_id(self):
        if self._dataset_id is None and (self.dmptool_alias and self.dataset_doi):
            connection = connect_from_settings_or_401(self)
            dmptool = connection.get_dmptool(self.dmptool_alias)
            dataset = dmptool.get_dataset_by_doi(self.dataset_doi)
            self._dataset_id = dataset.id
            self.save()
        return self._dataset_id

    @property
    def complete(self):
        return bool(self.has_auth)

    @property
    def folder_id(self):
        return self.dataset_id

    @property
    def folder_path(self):
        pass

    @property
    def nodelogger(self):
        # TODO: Use this for all log actions
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return DmptoolNodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, dmptool, dataset, auth=None):
        self.dmptool_alias = dmptool.alias
        self.dmptool = dmptool.title

        self.dataset_doi = dataset.doi
        self._dataset_id = dataset.id
        self.dataset = dataset.title

        self.save()

        if auth:
            self.owner.add_log(
                action='dmptool_dataset_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': dataset.title,
                },
                auth=auth,
            )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        try:
            return super(AddonDmptoolNodeSettings, self)._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError as e:
            # The Dmptool API returns a 404 if the dataset has no published files
            if e.code == http.NOT_FOUND and version == 'latest-published':
                return []
            raise

    def clear_settings(self):
        """Clear selected Dmptool and dataset"""
        self.dmptool_alias = None
        self.dmptool = None
        self.dataset_doi = None
        self._dataset_id = None
        self.dataset = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='dmptool_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_secret}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError("Dmptool is not configured")
        return {
            'host': self.external_account.oauth_key,
            'doi': self.dataset_doi,
            'id': self.dataset_id,
            'name': self.dataset,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='dmptool')
        self.owner.add_log(
            'dmptool_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.dataset,
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