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
from addons.nextcloudinstitutions import settings, apps
from osf.models.files import File, Folder, BaseFileNode

logger = logging.getLogger(__name__)

FULL_NAME = apps.FULL_NAME
SHORT_NAME = apps.SHORT_NAME

class NextcloudInstitutionsFileNode(BaseFileNode):
    _provider = SHORT_NAME


class NextcloudInstitutionsFolder(NextcloudInstitutionsFileNode, Folder):
    pass


class NextcloudInstitutionsFile(NextcloudInstitutionsFileNode, File):
    pass


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
            # logger.critical(item.path)
            count += 1
        return count

    @classmethod
    def can_access(cls, client):
        cls._list_count(client, '/')

    @classmethod
    def create_folder(cls, client, path):
        logger.info(u'create folder: {}'.format(path))
        client.mkdir(path)  # may raise
        return path

    @classmethod
    def remove_folder(cls, client, path):
        count = cls._list_count(client, path)
        if count != 0:
            raise exceptions.AddonError(u'cannot delete folder (not empty): {}'.format(path))
        logger.info(u'delete folder: {}'.format(path))
        client.delete(path)  # may raise
        return path

    @classmethod
    def rename_folder(cls, client, path_src, path_target):
        client.move(path_src, path_target)  # may raise

    @classmethod
    def root_folder_format(cls):
        return settings.ROOT_FOLDER_FORMAT

    def sync_contributors(self):
        # TODO
        pass

    def serialize_waterbutler_credentials_impl(self):
        provider = self.provider_switch(self.addon_option)
        return {
            'host': provider.host,
            'username': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings_impl(self):
        return {
            'folder': self.folder_id,
            'verify_ssl': settings.USE_SSL
        }

inst_utils.register(SHORT_NAME, NodeSettings)
