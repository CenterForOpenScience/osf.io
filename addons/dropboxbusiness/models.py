# -*- coding: utf-8 -*-
import httplib as http
import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from dropbox.dropbox import DropboxTeam
from dropbox.exceptions import DropboxException

from osf.models.node import Node
from osf.models.files import File, Folder, BaseFileNode
from osf.models.institution import Institution
from osf.models.rdm_addons import RdmAddonOption
from addons.base.models import (BaseNodeSettings, BaseStorageAddon)
from addons.base import exceptions
from addons.dropbox.models import Provider as DropboxProvider
from addons.dropboxbusiness import settings, utils
from addons.dropboxbusiness.apps import DropboxBusinessAddonAppConfig
from website import settings as website_settings
from framework.auth import Auth
from framework.exceptions import HTTPError
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
            val = self._history[-1]['extra']['hashes']['dropboxbusiness']
            return {'Dropbox content_hash': val,
                    'Dropbox Business content_hash': val,
                    'sha256': val}
        except (IndexError, KeyError):
            return None


class DropboxBusinessFileaccessProvider(DropboxProvider):
    name = 'Dropbox Business Team member file access'
    short_name = 'dropboxbusiness'

    client_id = settings.DROPBOX_BUSINESS_FILEACCESS_KEY
    client_secret = settings.DROPBOX_BUSINESS_FILEACCESS_SECRET

    is_allowed_default = False

    # Override : See addons.dropbox.models.Provider
    def auth_callback(self, user):
        # NOTE: "user" must be RdmAddonOption

        access_token = self.auth_callback_common()
        if access_token is None:
            return False
        self.client = DropboxTeam(access_token)
        info = self.client.team_get_info()

        if user.external_accounts.filter(
                provider=self.short_name,
                provider_id=info.team_id).exists():
            # use existing ExternalAccount and set it to the RdmAddonOption
            pass
        elif user.external_accounts.count() > 0:
            logger.info('Do not add multiple ExternalAccount for dropboxbusiness.')
            raise HTTPError(http.BAD_REQUEST)
        # else: create ExternalAccount and set it to the RdmAddonOption

        result = self._set_external_account(
            user,  # RdmAddonOption
            {
                'key': access_token,
                'provider_id': info.team_id,
                'display_name': info.name
            }
        )
        if result:
            try:
                utils.update_admin_dbmid(info.team_id)
            except Exception:
                pass
        return result


class DropboxBusinessManagementProvider(DropboxBusinessFileaccessProvider):
    name = 'Dropbox Business Team member management'
    short_name = 'dropboxbusiness_manage'

    client_id = settings.DROPBOX_BUSINESS_MANAGEMENT_KEY
    client_secret = settings.DROPBOX_BUSINESS_MANAGEMENT_SECRET


class NodeSettings(BaseNodeSettings, BaseStorageAddon):
    fileaccess_option = models.ForeignKey(
        RdmAddonOption, null=True, blank=True,
        related_name='dropboxbusiness_fileaccess_option',
        on_delete=models.CASCADE)
    management_option = models.ForeignKey(
        RdmAddonOption, null=True, blank=True,
        related_name='dropboxbusiness_management_option',
        on_delete=models.CASCADE)
    _admin_dbmid = models.CharField(null=True, blank=True, max_length=255)
    list_cursor = models.TextField(null=True, blank=True)
    team_folder_id = models.CharField(null=True, blank=True, max_length=255)
    group_id = models.CharField(null=True, blank=True, max_length=255)

    def _get_token(self, name):
        # fileacces_option, management_option
        option = getattr(self, '{}_option'.format(name.lower()), None)
        if not option:
            return None
        if name == 'fileaccess' and option.is_allowed is False:
            return None

        # DEBUG_FILEACCESS_TOKEN, DEBUG_MANAGEMENT_TOKEN
        debug = getattr(settings, 'DEBUG_{}_TOKEN'.format(name.upper()), None)
        if debug:
            return debug

        return utils.addon_option_to_token(option)

    @property
    def fileaccess_token(self):
        return self._get_token('fileaccess')

    @property
    def management_token(self):
        return self._get_token('management')

    @property
    def admin_dbmid(self):
        if settings.DEBUG_ADMIN_DBMID:
            return settings.DEBUG_ADMIN_DBMID
        if self._admin_dbmid:
            return self._admin_dbmid
        return None

    # Required (e.g. addons.base.apps.generic_root_folder)
    def fetch_folder_name(self):
        return self.folder_name

    # Required
    @property
    def folder_name(self):
        return '/ (Full Dropbox Business)'

    def team_folder_name(self):
        return u'{}{} ({})'.format(settings.TEAM_FOLDER_NAME_PREFIX,
                                   self.owner.title, self.owner._id)

    def group_name(self):
        return u'{}{}'.format(settings.GROUP_NAME_PREFIX, self.owner._id)

    def sync_members(self):
        members = [
            utils.eppn_to_email(c.eppn)
            for c in self.owner.contributors.all()
            if not c.is_disabled and c.eppn
        ]

        try:
            utils.sync_members(
                self.management_token,
                self.group_id,
                members
            )
        except DropboxException:
            logger.exception('Unexpected error')

    def rename_team_folder(self):
        try:
            fclient = DropboxTeam(self.fileaccess_token)
            fclient.team_team_folder_rename(
                self.team_folder_id,
                self.team_folder_name()
            )
        except DropboxException:
            logger.exception('Unexpected error')

    def create_team_folder(self, grdm_member_email_list, save=False):
        if not self.has_auth:
            return
        try:
            team_folder_id, group_id = utils.create_team_folder(
                self.fileaccess_token,
                self.management_token,
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
        if save:
            self.save()

    # Not override
    # def on_add(self):
    #     pass

    # Required
    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fileaccess_token}

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
        return self.fileaccess_token and self.management_token and \
            self.admin_dbmid

    def set_two_options(self, f_option, m_option, save=False):
        self.fileaccess_option = f_option
        self.management_option = m_option
        if save:
            self.save()

    def set_admin_dbmid(self, admin_dbmid, save=False):
        self._admin_dbmid = admin_dbmid
        if save:
            self.save()


# mount dropboxbusiness automatically
def init_addon(node, addon_name):
    if node.creator.eppn is None:
        # logger.info(u'{} has no ePPN.'.format(node.creator.username))
        return  # disabled
    institution_id = get_institution_id(node.creator)
    if institution_id is None:
        # logger.info(u'{} has no institution.'.format(node.creator.username))
        return  # disabled
    fm = utils.get_two_addon_options(institution_id)
    if fm is None:
        institution = Institution.objects.get(id=institution_id)
        logger.info(u'Institution({}) has no valid oauth keys.'.format(institution.name))
        return  # disabled

    f_option, m_option = fm
    f_account = utils.addon_option_to_token(f_option)
    m_account = utils.addon_option_to_token(m_option)
    if f_account is None or m_account is None:
        return  # disabled

    ### ----- enabled -----
    # checking the validity of Dropbox API here
    team_info = utils.TeamInfo(f_account, m_account)

    addon = node.add_addon(addon_name, auth=Auth(node.creator), log=True)
    addon.set_two_options(f_option, m_option)
    addon.set_admin_dbmid(team_info.admin_dbmid)

    #TODO create a group for admins and set the group to the team folder

    # On post_save of Node, self.owner.contributors is empty.
    addon.create_team_folder([utils.eppn_to_email(node.creator.eppn)],
                             save=True)


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
