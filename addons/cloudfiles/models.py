from django.db import models
from framework.auth.core import Auth
from rackspace import connection

from addons.base import exceptions
from addons.cloudfiles.serializer import CloudFilesSerializer

from addons.base.models import (BaseOAuthNodeSettings,
                                BaseOAuthUserSettings,
                                BaseStorageAddon)
from osf.models.files import (File,
                              Folder,
                              BaseFileNode)


class CloudFilesFileNode(BaseFileNode):
    _provider = 'cloudfiles'

    @property
    def _hashes(self):
        try:
            return self._history[-1]['extra']['hashes']
        except (IndexError, KeyError):
            return None


class CloudFilesFolder(CloudFilesFileNode, Folder):
    pass


class CloudFilesFile(CloudFilesFileNode, File):
    version_identifier = 'version'


class CloudFilesProvider(object):
    name = 'Cloud Files'
    short_name = 'cloudfiles'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = CloudFilesProvider
    serializer = CloudFilesSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = CloudFilesProvider
    serializer = CloudFilesSerializer

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    folder_region = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    FORBIDDEN_CHARS_FOR_CONTAINER_NAMES = ['/', '?']

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=save)

    def clear_settings(self):
        self.folder_id = None

    @property
    def folder_name(self):
        return self.folder_id

    @property
    def folder_path(self):
        return self.folder_id

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(NodeSettings, self).delete(save=save)

    def deauthorize(self, auth=None, log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a .save()

        if log:
            self.nodelogger.log(action='node_deauthorized')

    def set_folder(self, folder_id, region, **kwargs):

        self.folder_id = folder_id
        self.folder_region = region
        self.save()

        self.nodelogger.log(action='container_linked', save=True)

    def get_containers(self, region, **kwargs):

        conn = connection.Connection(username=self.external_account.provider_id,
                                     api_key=self.external_account.oauth_secret,
                                     region=region)
        return [
            {
                'addon': 'cloudfiles',
                'kind': 'folder',
                'id': container.name,
                'name': container.name,
                'path': container.name,
                'region': region,
                'urls': {
                    'folders': ''
                }
            }
            for container in conn.object_store.containers()
        ]

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Cannot serialize credentials for Cloud Files addon')
        return {
            'username': self.external_account.provider_id,
            'token': self.external_account.oauth_secret,
            'region': self.folder_region,
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for Cloud Files addon')
        return {
            'container': self.folder_id,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
                                     path=metadata['path'],
                                     provider='cloudfiles')

        self.owner.add_log(
            'cloudfiles_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'container': self.folder_id,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True)
