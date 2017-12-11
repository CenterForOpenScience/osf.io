# -*- coding: utf-8 -*-
import httplib as http

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
from osf.models.files import File, Folder, BaseFileNode
from framework.auth.core import _get_current_user
from addons.base import exceptions
from addons.dataverse.client import connect_from_settings_or_401
from addons.dataverse.serializer import DataverseSerializer
from addons.dataverse.utils import DataverseNodeLogger

class DataverseFileNode(BaseFileNode):
    _provider = 'dataverse'


class DataverseFolder(DataverseFileNode, Folder):
    pass


class DataverseFile(DataverseFileNode, File):
    version_identifier = 'version'

    @property
    def _hashes(self):
        try:
            return self._history[-1]['extra']['hashes']
        except (IndexError, KeyError):
            return None

    def update(self, revision, data, save=True, user=None):
        """Note: Dataverse only has psuedo versions, pass None to not save them
        Call super to update _history and last_touched anyway.
        Dataverse requires a user for the weird check below
        """
        version = super(DataverseFile, self).update(None, data, user=user, save=save)
        version.identifier = revision

        user = user or _get_current_user()
        if not user or not self.node.can_edit(user=user):
            try:
                # Users without edit permission can only see published files
                if not data['extra']['hasPublishedVersion']:
                    # Blank out name and path for the render
                    # Dont save because there's no reason to persist the change
                    self.name = ''
                    self.materialized_path = ''
                    return (version, '<div class="alert alert-info" role="alert">This file does not exist.</div>')
            except (KeyError, IndexError):
                pass
        return version


class DataverseProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""
    name = 'Dataverse'
    short_name = 'dataverse'
    serializer = DataverseSerializer

    def __init__(self, account=None):
        super(DataverseProvider, self).__init__()  # this does exactly nothing...
        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = DataverseProvider
    serializer = DataverseSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = DataverseProvider
    serializer = DataverseSerializer

    dataverse_alias = models.TextField(blank=True, null=True)
    dataverse = models.TextField(blank=True, null=True)
    dataset_doi = models.TextField(blank=True, null=True)
    _dataset_id = models.TextField(blank=True, null=True)
    dataset = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_name(self):
        return self.dataset

    @property
    def dataset_id(self):
        if self._dataset_id is None and (self.dataverse_alias and self.dataset_doi):
            connection = connect_from_settings_or_401(self)
            dataverse = connection.get_dataverse(self.dataverse_alias)
            dataset = dataverse.get_dataset_by_doi(self.dataset_doi)
            self._dataset_id = dataset.id
            self.save()
        return self._dataset_id

    @property
    def complete(self):
        return bool(self.has_auth and self.dataset_doi is not None)

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
        return DataverseNodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, dataverse, dataset, auth=None):
        self.dataverse_alias = dataverse.alias
        self.dataverse = dataverse.title

        self.dataset_doi = dataset.doi
        self._dataset_id = dataset.id
        self.dataset = dataset.title

        self.save()

        if auth:
            self.owner.add_log(
                action='dataverse_dataset_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': dataset.title,
                },
                auth=auth,
            )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        try:
            return super(NodeSettings, self)._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError as e:
            # The Dataverse API returns a 404 if the dataset has no published files
            if e.code == http.NOT_FOUND and version == 'latest-published':
                return []
            raise

    def clear_settings(self):
        """Clear selected Dataverse and dataset"""
        self.dataverse_alias = None
        self.dataverse = None
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
                action='dataverse_node_deauthorized',
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
            raise exceptions.AddonError('Dataverse is not configured')
        return {
            'host': self.external_account.oauth_key,
            'doi': self.dataset_doi,
            'id': self.dataset_id,
            'name': self.dataset,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='dataverse')
        self.owner.add_log(
            'dataverse_{0}'.format(action),
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
