from rest_framework import status as http_status

from addons.base import exceptions as addon_errors
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
from osf.models.files import File, Folder, BaseFileNode
from addons.base import exceptions
from addons.dataverse.client import connect_from_settings_or_401
from addons.dataverse.serializer import DataverseSerializer
from addons.dataverse.utils import DataverseNodeLogger

class DataverseFileNode(BaseFileNode):
    _provider = 'dataverse'

    @classmethod
    def get_or_create(cls, target, path, **query_params):
        '''Override get_or_create for Dataverse.

        Dataverse is weird and reuses paths, so we need to extract a "version"
        query param to determine which file to get. We also don't want to "create"
        here, as that might lead to integrity errors.
        '''
        version = query_params.get('version', None)
        if version not in {'latest', 'latest-published'}:
            raise addon_errors.QueryError(
                'Dataverse requires a "version" query paramater. '
                'Acceptable options are "latest" or "latest-published"'
            )

        content_type = ContentType.objects.get_for_model(target)
        try:
            obj = cls.objects.get(
                target_object_id=target.id,
                target_content_type=content_type,
                _path='/' + path.lstrip('/'),
                _history__0__extra__datasetVersion=version,
            )
        except cls.DoesNotExist:
            raise addon_errors.DoesNotExist(
                f'Requested Dataverse file does not exist with version "{version}"'
            )

        return obj


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
        """Note: Dataverse only has psuedo versions (_history), pass None to not save them
        Call super to update _history and last_touched anyway.
        """
        version = super().update(None, data, user=user, save=save)
        version.identifier = revision
        return version


class DataverseProvider:
    """An alternative to `ExternalProvider` not tied to OAuth"""
    name = 'Dataverse'
    short_name = 'dataverse'
    serializer = DataverseSerializer

    def __init__(self, account=None):
        super().__init__()  # this does exactly nothing...
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
            return super()._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError as e:
            # The Dataverse API returns a 404 if the dataset has no published files
            if e.code == http_status.HTTP_404_NOT_FOUND and version == 'latest-published':
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
            f'dataverse_{action}',
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

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
