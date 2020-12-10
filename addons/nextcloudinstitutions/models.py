# -*- coding: utf-8 -*-
import logging

from django.db import models
from owncloud import Client as NextcloudClient

from addons.base import exceptions
from addons.base import institutions_utils as inst_utils
from addons.base.institutions_utils import (
    InstitutionsNodeSettings,
    InstitutionsStorageAddon
)
from addons.nextcloud.models import NextcloudProvider
from addons.nextcloudinstitutions import settings, apps, utils
from osf.models.files import File, Folder, BaseFileNode
from osf.utils.permissions import ADMIN, READ, WRITE
from website.util import timestamp

logger = logging.getLogger(__name__)

FULL_NAME = apps.FULL_NAME
SHORT_NAME = apps.SHORT_NAME

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_{}: {}'.format(SHORT_NAME, msg))
    else:
        logger.debug(msg)

class NextcloudInstitutionsFileNode(BaseFileNode):
    _provider = SHORT_NAME


class NextcloudInstitutionsFolder(NextcloudInstitutionsFileNode, Folder):
    pass


class NextcloudInstitutionsFile(NextcloudInstitutionsFileNode, File):
    @property
    def _hashes(self):
        try:
            return self._history[-1]['extra']['hashes'][SHORT_NAME]
        except (IndexError, KeyError):
            return None

    # return (hash_type, hash_value)
    def get_hash_for_timestamp(self):
        hashes = self._hashes
        if hashes:
            if 'sha512' in hashes:
                return timestamp.HASH_TYPE_SHA512, hashes['sha512']
        return None, None  # unsupported

    def _my_node_settings(self):
        node = self.target
        if node:
            addon = node.get_addon(self.provider)
            if addon:
                return addon
        return None

    def get_timestamp(self):
        node_settings = self._my_node_settings()
        if node_settings:
            return utils.get_timestamp(
                node_settings,
                node_settings.root_folder_fullpath + self.path)
        return None, None, None

    def set_timestamp(self, timestamp_data, timestamp_status, context):
        node_settings = self._my_node_settings()
        if node_settings:
            utils.set_timestamp(
                node_settings,
                node_settings.root_folder_fullpath + self.path,
                timestamp_data, timestamp_status, context=context)


class NextcloudInstitutionsProvider(NextcloudProvider):
    name = FULL_NAME
    short_name = SHORT_NAME


class NodeSettings(InstitutionsNodeSettings, InstitutionsStorageAddon):
    FULL_NAME = FULL_NAME
    SHORT_NAME = SHORT_NAME

    folder_id = models.TextField(blank=True, null=True)

    @classmethod
    def addon_settings(cls):
        return settings

    @classmethod
    def get_provider(cls, external_account):
        return NextcloudInstitutionsProvider(external_account)

    @classmethod
    def get_debug_provider(cls):
        if not (settings.DEBUG_URL
                and settings.DEBUG_USER
                and settings.DEBUG_PASSWORD):
            return None

        class DebugProvider(object):
            host = settings.DEBUG_URL
            username = settings.DEBUG_USER
            password = settings.DEBUG_PASSWORD
        return DebugProvider()

    @classmethod
    def get_client(cls, provider):
        client = NextcloudClient(provider.host, verify_certs=settings.USE_SSL)
        client.login(provider.username, provider.password)
        return client

    @classmethod
    def _list_count(cls, client, path):
        count = 0
        for item in client.list(path):  # may raise
            count += 1
        return count

    @classmethod
    def can_access(cls, client, base_folder):
        path = cls.cls_fullpath(base_folder, '/')
        cls._list_count(client, path)

    @classmethod
    def create_folder(cls, client, base_folder, name):
        path = cls.cls_fullpath(base_folder, name)
        logger.info(u'create folder: {}'.format(path))
        client.mkdir(path)  # may raise

    @classmethod
    def remove_folder(cls, client, base_folder, name):
        path = cls.cls_fullpath(base_folder, name)
        count = cls._list_count(client, path)
        if count != 0:
            raise exceptions.AddonError(u'cannot delete folder (not empty): {}'.format(path))
        logger.info(u'delete folder: {}'.format(path))
        client.delete(path)  # may raise

    @classmethod
    def rename_folder(cls, client, base_folder, old_name, new_name):
        old = cls.cls_fullpath(base_folder, old_name)
        new = cls.cls_fullpath(base_folder, new_name)
        client.move(old, new)  # may raise

    @classmethod
    def root_folder_format(cls):
        return settings.ROOT_FOLDER_FORMAT

    @property
    def exists(self):
        try:
            self._list_count(self.client, self.root_folder_fullpath)
            return True
        except Exception:
            return False

    # override
    def sync_title(self):
        super(NodeSettings, self).sync_title()
        # share again to rename folder name for shared users
        self._delete_all_shares()
        self.sync_contributors()

    def _delete_all_shares(self):
        c = self.client
        for item in c.get_shares(path=self.root_folder_fullpath):
            if item.get_share_type() != c.OCS_SHARE_TYPE_USER:
                continue
            user_id = item.get_share_with()
            share_id = item.get_id()
            try:
                c.delete_share(share_id)
            except Exception as e:
                logger.warning(u'delete_share failed: user_id={}: {}'.format(user_id), str(e))

    def sync_contributors(self):
        node = self.owner
        c = self.client

        # 1 (read only)
        NC_READ = c.OCS_PERMISSION_READ
        # 7 (read, write, cannot DELETE)
        NC_WRITE = NC_READ | c.OCS_PERMISSION_UPDATE | c.OCS_PERMISSION_CREATE
        # 31 (NC_WRITE | OCS_PERMISSION_DELETE | OCS_PERMISSION_SHARE)
        NC_ADMIN = c.OCS_PERMISSION_ALL

        def _grdm_perms_to_nc_perms(node, user):
            if node.has_permission(user, ADMIN):
                return NC_ADMIN
            elif node.has_permission(user, WRITE):
                return NC_WRITE
            elif node.has_permission(user, READ):
                return NC_READ
            else:
                return None

        # nc_user_id -> (contributor(OSFUser), nc_permissions)
        grdm_member_all_dict = {}
        for cont in node.contributors.iterator():
            if cont.is_active and cont.eppn:
                nc_user_id = self.osfuser_to_extuser(cont)
                if not nc_user_id:
                    continue
                grdm_perms = node.get_permissions(cont)
                nc_perms = _grdm_perms_to_nc_perms(node, cont)
                if nc_perms is None:
                    continue
                grdm_member_all_dict[nc_user_id] = (cont, nc_perms)

        grdm_member_users = [
            user_id for user_id in grdm_member_all_dict.keys()
        ]

        # nc_user_id -> (nc_share_id, nc_permissions)
        nc_member_all_dict = {}
        for item in c.get_shares(path=self.root_folder_fullpath):  # may raise
            if item.get_share_type() == c.OCS_SHARE_TYPE_USER:
                nc_member_all_dict[item.get_share_with()] \
                    = (item.get_id(), item.get_permissions())

        nc_member_users = [
            user_id for user_id in nc_member_all_dict.keys()
        ]

        # share_file_with_user() cannot share a file with myself.
        my_user_id = self.provider.username
        grdm_member_users_set = set(grdm_member_users) - set([my_user_id])
        nc_member_users_set = set(nc_member_users) - set([my_user_id])

        add_users_set = grdm_member_users_set - nc_member_users_set
        remove_users_set = nc_member_users_set - grdm_member_users_set
        update_users_set = grdm_member_users_set & nc_member_users_set

        DEBUG(u'add_users_set: ' + str(add_users_set))
        DEBUG(u'remove_users_set: ' + str(remove_users_set))
        DEBUG(u'update_users_set: ' + str(update_users_set))

        first_exception = None
        for user_id in add_users_set:
            grdm_info = grdm_member_all_dict.get(user_id)
            if grdm_info is None:
                continue  # unexpected
            osfuser, perms = grdm_info
            try:
                c.share_file_with_user(self.root_folder_fullpath, user_id, perms=perms)
            except Exception as e:
                if first_exception:
                    first_exception = e
                logger.warning(u'share_file_with_user failed: user_id={}: {}'.format(user_id, str(e)))

        for user_id in remove_users_set:
            nc_info = nc_member_all_dict.get(user_id)
            if nc_info is None:
                continue  # unexpected
            share_id, perms = nc_info
            try:
                c.delete_share(share_id)
            except Exception as e:
                if first_exception:
                    first_exception = e
                logger.warning(u'delete_share failed: user_id={}: {}'.format(user_id, str(e)))

        for user_id in update_users_set:
            nc_info = nc_member_all_dict.get(user_id)
            if nc_info is None:
                continue  # unexpected
            share_id, nc_perms = nc_info
            grdm_info = grdm_member_all_dict.get(user_id)
            if grdm_info is None:
                continue  # unexpected
            osfuser, grdm_perms = grdm_info
            if nc_perms != grdm_perms:
                try:
                    c.update_share(share_id, perms=grdm_perms)
                except Exception as e:
                    if first_exception:
                        first_exception = e
                    logger.warning(u'update_share failed: user_id={}: {}'.format(user_id, str(e)))

        if first_exception:
            raise first_exception

    def serialize_waterbutler_credentials_impl(self):
        return {
            'host': self.provider.host,
            'username': self.provider.username,
            'password': self.provider.password
        }

    def serialize_waterbutler_settings_impl(self):
        return {
            'folder': self.root_folder_fullpath,
            'verify_ssl': settings.USE_SSL
        }

    def copy_folders(self, dest_addon):
        root_folder = '/' + self.root_folder_fullpath.strip('/') + '/'
        root_folder_len = len(root_folder)
        c = self.client
        destc = dest_addon.client
        for item in c.list(root_folder, depth='infinity'):  # may raise
            # print(item.path)
            if item.is_dir() and item.path.startswith(root_folder):
                subpath = item.path[root_folder_len:]
                newpath = dest_addon.root_folder_fullpath + '/' + subpath
                logger.debug(u'copy_folders: mkdir({})'.format(newpath))
                destc.mkdir(newpath)


inst_utils.register(NodeSettings)
