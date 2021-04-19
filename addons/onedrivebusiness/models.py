import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from osf.models.node import Node
from osf.models.contributor import Contributor
from website import settings as website_settings

import addons.onedrivebusiness.settings as settings
from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from addons.onedrivebusiness import SHORT_NAME, FULL_NAME
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer
from addons.onedrivebusiness.utils import get_region_external_account, get_user_map
from addons.onedrivebusiness.client import OneDriveBusinessClient
from addons.onedrive.models import OneDriveProvider
from framework.auth.core import Auth
from osf.models import ExternalAccount
from osf.models.files import File, Folder, BaseFileNode
from addons.onedrivebusiness import settings


logger = logging.getLogger(__name__)


class OneDriveBusinessFileNode(BaseFileNode):
    _provider = SHORT_NAME


class OneDriveBusinessFolder(OneDriveBusinessFileNode, Folder):
    pass


class OneDriveBusinessFile(OneDriveBusinessFileNode, File):
    version_identifier = 'version'


class OneDriveBusinessProvider(OneDriveProvider):
    name = FULL_NAME
    short_name = SHORT_NAME

    client_id = settings.ONEDRIVE_KEY
    client_secret = settings.ONEDRIVE_SECRET

    auth_url_base = settings.ONEDRIVE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['openid profile offline_access user.read.all files.readwrite.all']

    refresh_time = settings.REFRESH_TIME


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = OneDriveBusinessProvider
    serializer = OneDriveBusinessSerializer

    @property
    def has_auth(self):
        return True


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = OneDriveBusinessProvider
    serializer = OneDriveBusinessSerializer

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    folder_location = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = OneDriveBusinessProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def ensure_team_folder(self, region_external_account):
        region_provider = self.oauth_provider(region_external_account.external_account)
        try:
            access_token = region_provider.fetch_access_token()
        except exceptions.InvalidAuthError:
            raise HTTPError(403)
        region_client = OneDriveBusinessClient(access_token)
        node = self.owner
        folder_name = settings.TEAM_FOLDER_NAME_FORMAT.format(
            title=node.title, guid=node._id
        )
        region = region_external_account.region
        root_folder_id = region.waterbutler_settings['root_folder_id']
        if self.folder_id is not None:
            updated = self._update_team_folder(region_client, folder_name)
            updated = self._update_team_members(region_client, root_folder_id) or updated
            if updated:
                self.save()
            return
        folders = region_client.folders(folder_id=root_folder_id)
        folders = [f for f in folders if f['name'] == folder_name]
        if len(folders) > 0:
            folder = folders[0]
        else:
            folder = region_client.create_folder(root_folder_id, folder_name)
        logger.info('Folder: {}'.format(folder))
        self.folder_name = folder_name
        self.folder_id = folder['id']
        self._update_team_members(region_client, root_folder_id)
        if self.user_settings is None:
            self.user_settings = UserSettings.objects.create()
        self.save()

    @property
    def complete(self):
        return self.has_auth and self.folder_id is not None

    @property
    def has_auth(self):
        """Instance has *active* permission to use it"""
        return self.user_settings and self.user_settings.has_auth

    def authorize(self, user_settings, save=False):
        pass

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None

    def deauthorize(self, auth=None, log=True, save=False):
        if log:
            self.nodelogger.log(action='node_deauthorized', save=True)
        self.clear_settings()
        self.clear_auth()
        if save:
            self.save()

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(NodeSettings, self).delete(save=save)

    def fetch_access_token(self):
        region_external_account = get_region_external_account(self.owner)
        if region_external_account is None:
            raise exceptions.AddonError('Cannot retrieve credentials for {} addon'.format(FULL_NAME))
        region_provider = self.oauth_provider(region_external_account.external_account)
        return region_provider.fetch_access_token()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for {} addon'.format(FULL_NAME))
        return {
            'folder': self.folder_id
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider=SHORT_NAME)

        self.owner.add_log(
            '{0}_{1}'.format(SHORT_NAME, action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'folder': self.folder_name,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), log=True, save=True)

    def on_delete(self):
        self.deauthorize(log=False)
        self.save()

    def _update_team_folder(self, region_client, folder_name):
        if self.folder_name == folder_name:
            return False
        logger.info('Renaming {} -> {}'.format(self.folder_name, folder_name))
        region_client.rename_folder(self.folder_id, folder_name)
        self.folder_name = folder_name
        return True

    def _update_team_members(self, region_client, root_folder_id):
        user_map = get_user_map(region_client, root_folder_id)
        logger.info('Got user_map: {}'.format(user_map))
        return False


@receiver(post_save, sender=Node)
def node_post_save(sender, instance, created, **kwargs):
    if instance.is_deleted:
        return
    if SHORT_NAME not in website_settings.ADDONS_AVAILABLE_DICT:
        return
    region_external_account = get_region_external_account(instance)
    if region_external_account is None:
        return # disabled
    addon = instance.get_addon(SHORT_NAME)
    if addon is None:
        addon = instance.add_addon(SHORT_NAME, auth=Auth(instance.creator), log=True)
    addon.ensure_team_folder(region_external_account)
