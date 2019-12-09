# -*- coding: utf-8 -*-
import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from dropbox.dropbox import DropboxTeam
from dropbox.exceptions import DropboxException

from osf.models.node import Node
from osf.models.files import File, Folder, BaseFileNode
from addons.base.models import (BaseNodeSettings, BaseStorageAddon)
from addons.base import exceptions
from addons.dropboxbusiness import settings, utils
from addons.dropboxbusiness.apps import DropboxBusinessAddonAppConfig
from website import settings as website_settings
from admin.rdm_addons.utils import get_rdm_addon_option
from admin.rdm.utils import get_institution_id

logger = logging.getLogger(__name__)


class DropboxBusinessFileNode(BaseFileNode):
    _provider = 'dropboxbusiness'


class DropboxBusinessFolder(DropboxBusinessFileNode, Folder):
    pass


class DropboxBusinessFile(DropboxBusinessFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'Dropbox Business content_hash': self._history[-1]['extra']['hashes']['dropboxbusiness']}
        except (IndexError, KeyError):
            return None


class NodeSettings(BaseNodeSettings, BaseStorageAddon):
    file_access_token = settings.DEBUG_FILE_ACCESS_TOKEN
    management_access_token = settings.DEBUG_MANAGEMENT_ACCESS_TOKEN
    admin_dbmid = settings.DEBUG_ADMIN_DBMID

    team_folder_id = models.CharField(null=True, blank=True, max_length=255)
    group_id = models.CharField(null=True, blank=True, max_length=255)

    # Required (e.g. addons.base.apps.generic_root_folder)
    def fetch_folder_name(self):
        return self.folder_name

    # Required
    @property
    def folder_name(self):
        return '/ (Full Dropbox Business)'

    def team_folder_name(self):
        return u'{} ({})'.format(self.owner.title, self.owner._id)

    def group_name(self):
        return u'grdm-project-{}'.format(self.owner._id)

    def sync_members(self):
        """best effort sync_members
        """
        members = [
            utils.eppn_to_email(c.eppn)
            for c in self.owner.contributors.all()
            if not c.is_disabled and c.eppn
        ]

        try:
            utils.sync_members(
                self.management_access_token,
                self.group_id,
                members
            )
        except DropboxException:
            logger.exception('Unexpected error')

    def rename_team_folder(self):
        """best effort rename team folder
        """

        try:
            fclient = DropboxTeam(self.file_access_token)
            fclient.team_team_folder_rename(
                self.team_folder_id,
                self.team_folder_name()
            )
        except DropboxException:
            logger.exception('Unexpected error')

    def create_team_folder(self, grdm_member_email_list):
        """best effort create_team_folder
        """

        try:
            team_folder_id, group_id = utils.create_team_folder(
                self.file_access_token,
                self.management_access_token,
                self.admin_dbmid,
                self.team_folder_name(),
                self.group_name(),
                grdm_member_email_list
            )
        except DropboxException:
            logger.exception('Unexpected error')
            return

        self.team_folder_id = team_folder_id
        self.group_id = group_id
        self.save()

    def on_add(self):
        if not self.has_auth:  # no access tokens -> disabled
            return
        if self.complete:
            return

        # On post_save of Node, self.owner.contributors is empty.
        self.create_team_folder([utils.eppn_to_email(self.owner.creator.eppn)])

    # Required
    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.file_access_token}

    # Required
    def serialize_waterbutler_settings(self):
        if not self.configured:
            raise exceptions.AddonError('Addon is not configured')
        return {
            'folder': '/',
            'admin_dbmid': self.admin_dbmid,
            'team_folder_id': self.team_folder_id
        }

    # Required
    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
            path=metadata['path'].strip('/'),
            provider='dropboxbusiness'
        )
        self.owner.add_log(
            'dropboxbusiness_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': '/',
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            }
        )

    def __repr__(self):
        return u'<NodeSettings(node_id={self.owner._primary_key!r})>'.format(self=self)

    @property
    def complete(self):
        return self.has_auth and self.group_id and self.team_folder_id

    @property
    def configured(self):
        return self.complete

    @property
    def has_auth(self):
        return self.file_access_token and self.management_access_token and \
            self.admin_dbmid

def is_enabled(node, addon_name):
    institution_id = get_institution_id(node.creator)
    if institution_id is None:
        return False
    rdm_addon_option = get_rdm_addon_option(institution_id, addon_name)
    if rdm_addon_option:
        # TODO check two external accounts
        return True
    return False

def init_addon(node, addon_name):
    if is_enabled(node, addon_name):
        node.add_addon(addon_name, auth=None, log=True)

@receiver(post_save, sender=Node)
def on_node_updated(sender, instance, created, **kwargs):
    addon_name = DropboxBusinessAddonAppConfig.short_name
    if addon_name not in website_settings.ADDONS_AVAILABLE_DICT:
        return
    if created:
        init_addon(instance, addon_name)
    else:
        ns = instance.get_addon(addon_name)
        if ns is None or not ns.complete:  # disabled
            return
        ns.sync_members()
        ns.rename_team_folder()
