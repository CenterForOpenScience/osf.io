# -*- coding: utf-8 -*-
import abc
import six
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from osf.models.node import Node
from osf.models.rdm_addons import RdmAddonOption
from website import settings as website_settings
from website.project import signals as project_signals
from admin.rdm.utils import get_institution_id
from admin.rdm_addons.utils import get_rdm_addon_option
from addons.base import exceptions
from addons.base.models import BaseNodeSettings, BaseStorageAddon
from framework.auth import Auth

logger = logging.getLogger(__name__)

# The following functions are required in each models.py "for Institutions".
# - register()

ENABLED_ADDONS_FOR_INSTITUTIONS = []

# Keywords for RdmAddonOption.extended
KEYNAME_BASE_FOLDER = 'base_folder'
KEYNAME_USERMAP = 'usermap'
KEYNAME_USERMAP_TMP = 'usermap_tmp'

def register(node_settings_cls):
    name = node_settings_cls.SHORT_NAME
    ENABLED_ADDONS_FOR_INSTITUTIONS.append((name, node_settings_cls))


class InstitutionsNodeSettings(BaseNodeSettings):
    addon_option = models.ForeignKey(
        RdmAddonOption, null=True, blank=True, on_delete=models.CASCADE,
        related_name='%(app_label)s_node_settings')

    class Meta:
        abstract = True

    ###
    ### common methods:
    ###
    @property
    def complete(self):
        return self.has_auth and self.folder_id

    @property
    def has_auth(self):
        return self.addon_option

    @property
    def folder_path(self):
        return self.folder_id

    @property
    def folder_name(self):
        return self.folder_id

    def fetch_folder_name(self):
        return self.folder_id.strip('/').split('/')[-1]

    def clear_settings(self):
        self.folder_id = None

    def deauthorize(self, auth=None, add_log=True):
        self.clear_settings()
        self.addon_option = None
        self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('{} is not authorized'.format(
                self.FULL_NAME))
        return self.serialize_waterbutler_credentials_impl()

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('{} is not configured'.format(
                self.FULL_NAME))
        return self.serialize_waterbutler_settings_impl()

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
                                     path=metadata['path'],
                                     provider=self.SHORT_NAME)
        self.owner.add_log(
            '{}_{}'.format(self.SHORT_NAME, action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
                'path': metadata['materialized'].lstrip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)

    def after_fork(self, node, fork, user, save=True):
        # Storage Addon for Insstitutions cannot use parent NodeSettings.
        pass

    def after_template(self, tmpl_node, new_node, user, save=True):
        if not self.has_auth:
            return
        dest_addon = new_node.get_addon(self.SHORT_NAME)  # same provider
        if not dest_addon:
            return
        if not dest_addon.has_auth:
            return
        try:
            self.copy_folders(dest_addon)
        except Exception as e:
            logger.exception(u'cannot copy folders: {}'.format(str(e)))
            # Do not raise

    def on_delete(self):
        self.deauthorize(add_log=False)

    ###
    ### required methods:
    ###
    @abc.abstractproperty
    def FULL_NAME(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def SHORT_NAME(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def folder_id(self):
        raise NotImplementedError()

    def serialize_waterbutler_credentials_impl(self):
        raise NotImplementedError()

    def serialize_waterbutler_settings_impl(self):
        raise NotImplementedError()

    def copy_folders(self, dest_addon):
        raise NotImplementedError()


class InstitutionsStorageAddon(BaseStorageAddon):
    ###
    ### common methods:
    ###
    @classmethod
    def get_addon_option(cls, institution_id, addon_short_name):
        addon_option = get_rdm_addon_option(
            institution_id, addon_short_name,
            create=False)
        if addon_option is None:
            return None
        if not addon_option.is_allowed:
            return None
        return addon_option

    @classmethod
    def provider_switch(cls, addon_option):
        provider = cls.get_debug_provider()
        if provider is not None:
            return provider
        exacc = addon_option.get_one_external_account()
        if exacc is None:
            logger.info('No external account for institution_id={}'.format(addon_option.institution.id))
            return  # disabled
        return cls.get_provider(exacc)

    @classmethod
    def init_addon(cls, node, institution_id, addon_name):
        addon_option = cls.get_addon_option(institution_id, addon_name)
        if addon_option is None:
            logger.debug('No addon option for institution_id={}, addon_name={}'.format(institution_id, addon_name))
            return None  # disabled

        provider = cls.provider_switch(addon_option)
        client = cls.get_client(provider)
        cls.can_access(client)
        root_folder = cls.create_root_folder(addon_option, client, node)
        try:
            addon = node.add_addon(addon_name, auth=Auth(node.creator),
                                   log=True)
            addon.set_addon_option(addon_option)
            addon.set_folder(root_folder)
            addon.save()
            return addon
        except Exception:
            try:
                cls.remove_folder(provider, client, root_folder)
            except Exception:
                logger.error(u'cannot remove unnecessary folder: ({})/{}'.format(addon_name, root_folder))
            raise

    @classmethod
    def base_folder(cls, addon_option):
        extended = addon_option.extended
        if extended:
            base_folder = extended.get(KEYNAME_BASE_FOLDER)
            if base_folder:
                return base_folder
        try:
            addon_settings = cls.addon_settings()
            if addon_settings.DEFAULT_BASE_FOLDER:
                return addon_settings.DEFAULT_BASE_FOLDER
        except Exception:
            pass  # no DEFAULT_BASE_FOLDER
        return ''

    # root_folder=BASE_FOLDR/ROOT_FOLDER_FORMAT
    @classmethod
    def root_folder(cls, addon_option, node):
        base_folder = cls.base_folder(addon_option)
        title = cls.filename_filter(node.title)
        fmt = six.u(cls.root_folder_format())
        return u'{}/{}'.format(base_folder,
                               fmt.format(title=title, guid=node._id))

    @classmethod
    def create_root_folder(cls, addon_option, client, node):
        root_folder = cls.root_folder(addon_option, node)
        return cls.create_folder(client, root_folder)

    @classmethod
    def filename_filter(cls, name):
        return name.replace('/', '_')

    def set_addon_option(self, addon_option):
        self.addon_option = addon_option

    def set_folder(self, folder, auth=None):
        self.folder_id = folder

    def sync_title(self):
        new_root_folder = self.root_folder(self.addon_option, self.owner)
        if self.folder_id == new_root_folder:
            return
        try:
            self.rename_folder(self.client, self.folder_id, new_root_folder)
        except Exception:
            logger.error(u'rename_folder({}, {}) failed'.format(self.folder_id, new_root_folder))
            raise
        self.set_folder(new_root_folder)
        self.save()

    _client = None
    _provider = None

    @property
    def provider(self):
        if self._provider is None:
            self._provider = self.provider_switch(self.addon_option)
        return self._provider

    @property
    def client(self):
        if self._client is None:
            self._client = self.get_client(self.provider)
        return self._client

    def osfuser_to_extuser(self, osfuser):
        guid = osfuser._id
        addon_settings = self.addon_settings()
        if addon_settings.DEBUG_USERMAP is not None:
            logger.warning(u'{}: DEBUG_USERMAP is enabled, User mapping from CSV is not used.'.format(self.SHORT_NAME))
            ncuser = addon_settings.DEBUG_USERMAP.get(guid)
            if not ncuser:  # case insensitive
                ncuser = addon_settings.DEBUG_USERMAP.get(guid.upper())
            if ncuser:
                return ncuser
        extended = self.addon_option.extended
        osfuser_to_extuser = extended.get(KEYNAME_USERMAP)
        if osfuser_to_extuser:
            extuser = osfuser_to_extuser.get(guid)
            if extuser:
                return extuser
        return None

    ###
    ### required methods:
    ###
    @classmethod
    def addon_settings(cls):
        raise NotImplementedError()

    @classmethod
    def get_provider(cls, external_account):
        raise NotImplementedError()

    @classmethod
    def get_debug_provider(cls):
        raise NotImplementedError()

    @classmethod
    def get_client(cls, provider):
        raise NotImplementedError()

    @classmethod
    def can_access(cls, client):
        raise NotImplementedError()

    @classmethod
    def create_folder(cls, client, path):
        raise NotImplementedError()

    @classmethod
    def remove_folder(cls, client, path):
        raise NotImplementedError()

    @classmethod
    def rename_folder(cls, client, path_src, path_target):
        raise NotImplementedError()

    @classmethod
    def root_folder_format(cls):
        raise NotImplementedError()

    def sync_contributors(self):
        raise NotImplementedError()


# store values in a short time to detect changed fields
class SyncInfo(object):
    sync_info_dict = {}  # Node.id -> SyncInfo

    def __init__(self):
        self.old_node_title = None

    @classmethod
    def get(cls, id):
        info = cls.sync_info_dict.get(id)
        if info is None:
            info = SyncInfo()
            cls.sync_info_dict[id] = info
        return info


@receiver(pre_save, sender=Node)
def node_pre_save(sender, instance, **kwargs):
    if instance.is_deleted:
        return
    try:
        # instance is not save()d yet.
        old_node = Node.objects.get(id=instance.id)
        syncinfo = SyncInfo.get(old_node.id)
        syncinfo.old_node_title = old_node.title
    except Exception:
        # may not exist
        pass

@receiver(post_save, sender=Node)
def node_post_save(sender, instance, created, **kwargs):
    node = instance
    if node.is_deleted:
        return
    if not hasattr(node, 'get_addon'):
        return
    if created:  # node is created
        if node.creator.eppn is None:
            logger.error(u'{} has no ePPN.'.format(node.creator.username))
            return  # disabled

        institution_id = get_institution_id(node.creator)
        if institution_id is None:
            logger.error(u'user={} has no institution.'.format(node.creator.username))
            return  # disabled

        logger.debug(u'ENABLED_ADDONS_FOR_INSTITUTIONS={}, website_settings.ADDONS_AVAILABLE_DICT={}, website_settings.ADDONS_AVAILABLE={}'.format(str(ENABLED_ADDONS_FOR_INSTITUTIONS), str(website_settings.ADDONS_AVAILABLE_DICT), str(website_settings.ADDONS_AVAILABLE)))

        for addon_name, node_settings_cls in ENABLED_ADDONS_FOR_INSTITUTIONS:
            if addon_name not in website_settings.ADDONS_AVAILABLE_DICT:
                continue  # skip
            node_settings_cls.init_addon(node, institution_id, addon_name)
            ### NOTE: This is no effect,
            ###   because node.creator is not added to Contributor yet here.
            # if ns:
            #     ns.sync_contributors()
    else:
        sync_title(node)

def sync_title(node, target_addons=None, force=False):
    old_node_title = None
    if force is False:
        syncinfo = SyncInfo.get(node.id)
        if node.title == syncinfo.old_node_title:
            return  # skip
        old_node_title = syncinfo.old_node_title

    for addon_name, node_settings_cls in ENABLED_ADDONS_FOR_INSTITUTIONS:
        if addon_name not in website_settings.ADDONS_AVAILABLE_DICT:
            continue  # skip
        if target_addons and addon_name not in target_addons:
            continue  # skip
        ns = node.get_addon(addon_name)  # get NodeSetttings
        if ns is None or not ns.complete:  # disabled
            continue  # skip
        try:
            ns.sync_title()
        except Exception:
            logger.warning(u'cannot rename root folder: addon_name={}, old_title={}, new_title={}, GUID={}'.format(addon_name, old_node_title, node.title, node._id))

@project_signals.contributors_updated.connect
def sync_contributors(node, target_addons=None):
    if node.is_deleted:
        return
    if not hasattr(node, 'get_addon'):
        return
    for addon_name, node_settings_cls in ENABLED_ADDONS_FOR_INSTITUTIONS:
        if addon_name not in website_settings.ADDONS_AVAILABLE_DICT:
            continue  # skip
        if target_addons and addon_name not in target_addons:
            continue  # skip
        ns = node.get_addon(addon_name)  # get NodeSetttings
        if ns is None or not ns.complete:  # disabled
            continue  # skip
        try:
            ns.sync_contributors()
        except Exception as e:
            logger.error(str(e))
            logger.warning(u'cannot synchronize contributors: addon_name={}, title={}, GUID={}'.format(addon_name, node.title, node._id))


from celery.contrib.abortable import AbortableTask
from framework.celery_tasks import app as celery_app

@celery_app.task(bind=True, base=AbortableTask)
def celery_sync_all(self, institution_id, target_addons=None):
    for n in Node.objects.filter(affiliated_institutions___id=institution_id,
                                 is_deleted=False):
        sync_title(n, target_addons=target_addons, force=True)
        sync_contributors(n, target_addons=target_addons)

def sync_all(institution_id, target_addons=None):
    celery_sync_all.delay(institution_id, target_addons=target_addons)
