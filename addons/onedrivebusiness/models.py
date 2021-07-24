import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from framework.exceptions import HTTPError
from osf.models.node import Node
from website import settings as website_settings

import addons.onedrivebusiness.settings as settings
from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from addons.onedrivebusiness import SHORT_NAME, FULL_NAME
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer
from addons.onedrivebusiness.utils import (parse_root_folder_id,
                                           get_region_external_account,
                                           get_user_map)
from addons.onedrivebusiness.client import OneDriveBusinessClient
from addons.onedrive.models import OneDriveProvider
from framework.auth.core import Auth
from osf.models.files import File, Folder, BaseFileNode


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

    drive_id = models.TextField(blank=True, null=True)
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
        node = self.owner
        folder_name = settings.TEAM_FOLDER_NAME_FORMAT.format(
            title=node.title, guid=node._id
        )
        region = region_external_account.region
        root_folder_id = region.waterbutler_settings['root_folder_id']
        r_drive_id, r_folder_id = parse_root_folder_id(root_folder_id)
        region_client = OneDriveBusinessClient(access_token, drive_id=r_drive_id)
        if self.folder_id is not None:
            updated = self._update_team_folder(region_client, folder_name)
            updated = self._update_team_members(region_client, r_folder_id) or updated
            if updated:
                self.save()
            return
        folders = region_client.folders(folder_id=r_folder_id)
        folders = [f for f in folders if f['name'] == folder_name]
        if len(folders) > 0:
            folder = folders[0]
        else:
            folder = region_client.create_folder(r_folder_id, folder_name)
        logger.info('Folder: {}'.format(folder))
        self.folder_name = folder_name
        self.drive_id = r_drive_id
        self.folder_id = folder['id']
        self._update_team_members(region_client, r_folder_id)
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
            'drive': self.drive_id,
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
        permissions = region_client.get_permissions(self.folder_id)
        logger.debug('Permissions: {}'.format(permissions))
        contributors = []
        for c in self.owner.contributors:
            if c.eppn is None:
                logger.warning('User {} has no ePPN'.format(c._id))
                continue
            if c.eppn not in user_map:
                logger.warning('User {} has no MS account'.format(c._id))
                continue
            contributors.append((user_map[c.eppn], self.owner.can_edit(user=c)))
        logger.info('Contributors: {}'.format(contributors))
        for contributor, editable in contributors:
            matched_permission = None
            for permission in permissions['value']:
                if 'grantedTo' not in permission:
                    continue
                if 'user' not in permission['grantedTo']:
                    continue
                if permission['grantedTo']['user']['id'] == contributor['id']:
                    matched_permission = permission
            if matched_permission is None:
                # New user
                roles = ['write'] if editable else ['read']
                region_client.invite_user(self.folder_id, contributor['mail'], roles)
            elif editable and len(set(permission['roles']) & {'write', 'owner'}) == 0:
                # Make writable
                roles = ['write']
                region_client.update_permission(self.folder_id, matched_permission['id'], roles)
            elif not editable and len(set(permission['roles']) & {'write', 'owner'}) > 0:
                # Make not writable
                roles = ['read']
                region_client.update_permission(self.folder_id, matched_permission['id'], roles)
        contributor_ids = set([c['id'] for c, _ in contributors])
        for permission in permissions['value']:
            if 'grantedTo' not in permission:
                continue
            if 'user' not in permission['grantedTo']:
                continue
            if 'owner' in permission['roles']:
                continue
            if permission['grantedTo']['user']['id'] in contributor_ids:
                continue
            # Revoke permission
            region_client.remove_permission(self.folder_id, permission['id'])
        return False


@receiver(post_save, sender=Node)
def node_post_save(sender, instance, created, **kwargs):
    if instance.is_deleted:
        return
    if SHORT_NAME not in website_settings.ADDONS_AVAILABLE_DICT:
        return
    region_external_account = get_region_external_account(instance)
    if region_external_account is None:
        return  # disabled
    addon = instance.get_addon(SHORT_NAME)
    if addon is None:
        addon = instance.add_addon(SHORT_NAME, auth=Auth(instance.creator), log=True)
    addon.ensure_team_folder(region_external_account)
