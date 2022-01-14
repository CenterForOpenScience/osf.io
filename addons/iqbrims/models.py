# -*- coding: utf-8 -*-
"""Persistence layer for the IQB-RIMS addon.
"""
import os
import json
import logging
import random
import string

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from django.db.models import Subquery
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf.models.node import Node
from osf.models.user import OSFUser
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from osf.models import Contributor, RdmAddonOption, AbstractNode
from addons.googledrive.apps import GoogleDriveAddonConfig
from addons.googledrive.models import NodeSettings as GDNodeSettings
from addons.base import exceptions
from addons.iqbrims import settings as drive_settings
from addons.iqbrims.apps import IQBRIMSAddonConfig
from addons.iqbrims.client import (IQBRIMSAuthClient,
                                               IQBRIMSClient)
from addons.iqbrims.serializer import IQBRIMSSerializer
from addons.iqbrims.utils import (to_hgrid, get_folder_title, copy_node_auth,
                                  oauth_disconnect_following_other)
from website.util import api_v2_url
from website import settings as ws_settings

# from website.files.models.ext import PathFollowingFileNode

logger = logging.getLogger(__name__)

REVIEW_FOLDERS = {'paper': u'最終原稿・組図',
                  'raw': u'生データ',
                  'checklist': u'チェックリスト',
                  'scan': u'スキャン結果'}
REVIEW_FILE_LIST = '.files.txt'


# TODO make iqbrims "pathfollowing"
# A migration will need to be run that concats
# folder_path and filenode.path
# class IQBRIMSFileNode(PathFollowingFileNode):
class IQBRIMSFileNode(BaseFileNode):
    _provider = 'iqbrims'
    FOLDER_ATTR_NAME = 'folder_path'


class IQBRIMSFolder(IQBRIMSFileNode, Folder):
    pass


class IQBRIMSFile(IQBRIMSFileNode, File):
    pass


class IQBRIMSProvider(ExternalProvider):
    name = 'IQB-RIMS'
    short_name = 'iqbrims'

    client_id = drive_settings.CLIENT_ID
    client_secret = drive_settings.CLIENT_SECRET

    auth_url_base = '{}{}'.format(drive_settings.OAUTH_BASE_URL, 'auth?access_type=offline&approval_prompt=force')
    callback_url = '{}{}'.format(drive_settings.API_BASE_URL, 'oauth2/v3/token')
    auto_refresh_url = callback_url
    refresh_time = drive_settings.REFRESH_TIME
    expiry_time = drive_settings.EXPIRY_TIME

    default_scopes = drive_settings.OAUTH_SCOPE
    _auth_client = IQBRIMSAuthClient()
    _drive_client = IQBRIMSClient()

    def handle_callback(self, response):
        client = self._auth_client
        info = client.userinfo(response['access_token'])
        return {
            'provider_id': info['sub'],
            'display_name': info['name'],
            'profile_url': info.get('profile', None)
        }

    def fetch_access_token(self, force_refresh=False):
        refreshed = self.refresh_oauth_key(force=force_refresh)
        logger.debug('refresh_oauth_key returns {}'.format(refreshed))
        return self.account.oauth_key


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = IQBRIMSProvider
    serializer = IQBRIMSSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = IQBRIMSProvider
    provider_name = 'iqbrims'

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    serializer = IQBRIMSSerializer
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)
    status = models.TextField(blank=True, null=True)
    secret = models.TextField(blank=True, null=True)
    process_definition_id = models.TextField(blank=True, null=True)

    _api = None

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = IQBRIMSProvider(self.external_account)
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        ))

    @property
    def folder_name(self):
        if not self.folder_id:
            return None

        if self.folder_path != '/':
            return os.path.split(self.folder_path)[1]
        else:
            return '/ (Full IQB-RIMS)'

    def clear_settings(self):
        self.folder_id = None
        self.folder_path = None

    def get_folders(self, **kwargs):
        node = self.owner

        #  Defaults exist when called by the API, but are `None`
        path = kwargs.get('path') or ''
        folder_id = kwargs.get('folder_id') or 'root'

        try:
            access_token = self.fetch_access_token()
        except exceptions.InvalidAuthError:
            raise HTTPError(403)

        client = IQBRIMSClient(access_token)
        if folder_id == 'root':
            about = client.about()

            return [{
                'addon': self.config.short_name,
                'path': '/',
                'kind': 'folder',
                'id': about['rootFolderId'],
                'name': '/ (Full IQB-RIMS)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(self.owner._id),
                        params={
                            'path': '/',
                            'id': about['rootFolderId']
                    })
                }
            }]

        contents = [
            to_hgrid(item, node, path=path)
            for item in client.folders(folder_id)
        ]
        return contents

    def set_folder(self, folder, auth):
        """Configure this addon to point to a IQB-RIMS folder

        :param dict folder:
        :param User user:
        """
        self.folder_id = folder['id']
        self.folder_path = folder['path']

        # Tell the user's addon settings that this node is connecting
        self.user_settings.grant_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        )  # Performs a save on self.user_settings
        self.save()

        self.nodelogger.log('folder_selected', save=True)

    @property
    def selected_folder_name(self):
        if self.folder_id is None:
            return ''
        elif self.folder_id == 'root':
            return 'Full IQB-RIMS'
        else:
            return self.folder_name

    def deauthorize(self, auth=None, add_log=True, save=False):
        """Remove user authorization from this node and log the event."""

        if add_log:
            extra = {'folder_id': self.folder_id}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_settings()
        self.clear_auth()

        if save:
            self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Folder is not configured')
        status = self.get_status()
        permissions = [(fname,
                        status['workflow_' + fid + '_permissions']
                        if 'workflow_' + fid + '_permissions' in status else
                        [])
                       for fid, fname in REVIEW_FOLDERS.items()]
        return {
            'folder': {
                'id': self.folder_id,
                'name': self.folder_name,
                'path': self.folder_path
            },
            'permissions': dict(permissions)
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='iqbrims')

        self.owner.add_log(
            'iqbrims_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder_path,

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True, save=True)

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def get_status(self):
        if self.status is None or self.status == '':
            return {'state': 'initialized'}
        return json.loads(self.status)

    def set_status(self, status):
        assert 'state' in status
        self.status = json.dumps(status)
        self.save()

    def get_process_definition_id(self, user_settings=None, register_type=None):
        if register_type is None:
            return self.process_definition_id
        app_id = None
        assert user_settings is not None
        if register_type == 'deposit':
            app_id = user_settings.FLOWABLE_RESEARCH_APP_ID
        elif register_type == 'check':
            app_id = user_settings.FLOWABLE_SCAN_APP_ID
        else:
            return None
        if self.process_definition_id is None:
            self.process_definition_id = app_id
            self.save()
        return app_id

    def get_secret(self):
        if self.secret is not None:
            return self.secret
        secret = [random.choice(string.ascii_letters + string.digits)
                  for i in range(0, 16)]
        self.secret = ''.join(secret)
        self.save()
        return self.secret


@receiver(post_save, sender=Node)
def add_iqbrims_addon(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return

    inst_ids = instance.affiliated_institutions.values('id')
    addon_option = RdmAddonOption.objects.filter(
        provider=IQBRIMSAddonConfig.short_name,
        institution_id__in=Subquery(inst_ids),
        management_node__isnull=False,
        is_allowed=True
    ).first()
    if addon_option is None:
        return
    if addon_option.organizational_node is not None and \
            not addon_option.organizational_node.is_contributor(instance.creator):
        return

    instance.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)

@receiver(m2m_changed, sender=OSFUser.external_accounts.through)
def follow_googledrive_external_account_to_iqbrims(sender, instance, action, **kwargs):
    if not action.startswith('post'):
        return
    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return
    if not instance.has_addon(IQBRIMSAddonConfig.short_name):
        return
    if not instance.has_addon(GoogleDriveAddonConfig.short_name):
        return

    oauth_disconnect_following_other(instance, instance.get_addon(GoogleDriveAddonConfig.short_name))

@receiver(post_save, sender=GDNodeSettings)
def follow_googledrive_node_settings_to_iqbrims(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return

    node = instance.owner
    is_management_node = RdmAddonOption.objects.filter(
        provider=IQBRIMSAddonConfig.short_name,
        management_node=node,
        is_allowed=True
    ).exists()

    if is_management_node and node.has_addon(IQBRIMSAddonConfig.short_name):
        copy_node_auth(node, instance, None)

@receiver(post_save, sender=Contributor)
@receiver(post_delete, sender=Contributor)
def change_iqbrims_addon_enabled_for_contrib(sender, instance, **kwargs):
    from osf.models import Node, RdmAddonOption

    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return

    organizational_node = instance.node
    rdm_addon_options = RdmAddonOption.objects.filter(
        provider=IQBRIMSAddonConfig.short_name,
        is_allowed=True,
        management_node__isnull=False,
        organizational_node=organizational_node
    ).all()

    for rdm_addon_option in rdm_addon_options:
        for node in Node.find_by_institutions(rdm_addon_option.institution):
            if organizational_node.is_contributor(node.creator):
                node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
            else:
                node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)

@receiver(post_save, sender=Node)
def update_folder_name(sender, instance, created, **kwargs):
    node = instance
    if not node.has_addon(IQBRIMSAddonConfig.short_name):
        return
    iqbrims = node.get_addon(IQBRIMSAddonConfig.short_name)
    if not iqbrims.has_auth:
        return
    if RdmAddonOption.objects.filter(
        provider=IQBRIMSAddonConfig.short_name,
        management_node=node
    ).exists():
        return
    try:
        access_token = iqbrims.fetch_access_token()
        client = IQBRIMSClient(access_token)
        folder_info = client.get_folder_info(folder_id=iqbrims.folder_id)
        new_title = get_folder_title(node)
        current_title = folder_info['title']
        if current_title != new_title:
            logger.info(u'Update: title={}, current={}'.format(new_title, current_title))
            client.rename_folder(iqbrims.folder_id, new_title)
        else:
            logger.info(u'No changes: title={}, current={}'.format(new_title, current_title))
    except exceptions.InvalidAuthError:
        logger.warning('Failed to check description of google drive',
                       exc_info=True)

@receiver(post_save, sender=RdmAddonOption)
def change_iqbrims_addon_enabled(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return

    if instance.is_allowed and instance.management_node is not None:
        for node in AbstractNode.find_by_institutions(instance.institution):
            if instance.organizational_node:
                if instance.organizational_node.is_contributor(node.creator):
                    node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
                else:
                    node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)
            else:
                node.add_addon(IQBRIMSAddonConfig.short_name, auth=None, log=False)
    else:
        for node in AbstractNode.find_by_institutions(instance.institution):
            node.delete_addon(IQBRIMSAddonConfig.short_name, auth=None)

@receiver(post_save, sender=RdmAddonOption)
def setup_iqbrims_addon_auth_of_management_node(sender, instance, created, **kwargs):
    if IQBRIMSAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return
    if GoogleDriveAddonConfig.short_name not in ws_settings.ADDONS_AVAILABLE_DICT:
        return
    if instance.management_node is None:
        return
    if not (instance.is_allowed and instance.management_node is not None):
        return

    copy_node_addon = instance.management_node.get_addon(GoogleDriveAddonConfig.short_name)
    if copy_node_addon is not None:
        copy_node_auth(instance.management_node, copy_node_addon,
                       Auth(instance.management_node.creator))
