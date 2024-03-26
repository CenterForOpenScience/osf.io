# -*- coding: utf-8 -*-
from datetime import timedelta, datetime
import logging
import re

from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from framework.auth.decorators import Auth

from osf.models.base import BaseModel
from osf.models.files import File, Folder, BaseFileNode
from osf.models.nodelog import NodeLog
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from website import settings as website_settings

from addons.metadata import SHORT_NAME as METADATA_SHORT_NAME

from .serializer import WEKOSerializer
from .provider import WEKOProvider
from .client import Client
from .apps import SHORT_NAME, FULL_NAME
from .deposit import ROCRATE_FILENAME_PATTERN
from . import settings


logger = logging.getLogger(__name__)


class WEKOFileNode(BaseFileNode):
    _provider = 'weko'


class WEKOFolder(WEKOFileNode, Folder):
    pass


class WEKOFile(WEKOFileNode, File):
    version_identifier = 'version'

class UserSettings(BaseOAuthUserSettings):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer

    index_title = models.TextField(blank=True, null=True)
    index_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = WEKOProvider(self.external_account)
        return self._api

    @property
    def folder_name(self):
        return self.index_title

    @property
    def complete(self):
        return bool(self.has_auth and self.index_id is not None)

    @property
    def folder_id(self):
        return self.index_id

    @property
    def folder_path(self):
        pass

    @property
    def has_metadata(self):
        return self.complete

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    def create_client(self):
        if not self.external_account:
            return None
        provider = WEKOProvider(self.external_account)

        if provider.repoid is None:
            # Basic authentication - for compatibility
            return Client(provider.sword_url, username=provider.userid,
                          password=provider.password)
        token = provider.fetch_access_token()
        return Client(provider.sword_url, token=token)

    def set_folder(self, index_id, auth=None):
        c = self.create_client()
        index = c.get_index_by_id(index_id)

        self.index_id = index.identifier
        self.index_title = index.title

        self.save()

        if auth:
            self.owner.add_log(
                action='weko_index_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': index.title,
                },
                auth=auth,
            )
        return index

    def set_publish_task_id(self, path, task_id):
        q = self.publish_task.filter(path=path).order_by('-updated')
        if not q.exists():
            self._clean_expired_publish_tasks()
            PublishTask.objects.create(
                project=self,
                path=path,
                updated=timezone.now(),
                last_task_id=task_id
            )
            return
        m = q.first()
        m.updated = timezone.now()
        m.last_task_id = task_id
        m.save()

    def get_publish_task_id(self, path):
        q = self.publish_task.filter(path=path).order_by('-updated')
        if not q.exists():
            return None
        m = q.first()
        if timezone.now() - m.updated > timedelta(days=1):
            return None
        return {
            'task_id': m.last_task_id,
            'updated': m.updated.timestamp(),
        }

    def clear_settings(self):
        """Clear selected index"""
        self.index_id = None
        self.index_title = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            try:
                self.owner.add_log(
                    action='weko_node_deauthorized',
                    params={
                        'project': node.parent_id,
                        'node': node._id,
                    },
                    auth=auth,
                )
            except Exception as e:
                logger.exception('Error when deauthorizing node {0} for user {1}'.format(node._id, self.owner._id))
                raise e

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        provider = WEKOProvider(self.external_account)
        default_provider = self.get_default_provider()
        r = {
            'default_storage': default_provider.serialize_waterbutler_credentials(),
        }
        if provider.repoid is not None:
            r.update({
                'token': self.fetch_access_token(),
                'user_id': provider.userid,
            })
        else:
            r.update({
                'password': provider.password,
                'user_id': provider.userid,
            })
        return r

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('WEKO is not configured')
        provider = WEKOProvider(self.external_account)
        default_provider = self.get_default_provider()
        return {
            'nid': self.owner._id,
            'url': provider.sword_url,
            'index_id': self.index_id,
            'index_title': self.index_title,
            'default_storage': default_provider.serialize_waterbutler_settings(),
        }

    def create_waterbutler_log(self, auth, action, metadata):
        if action in ['file_added', 'folder_created'] and self._is_top_level_draft(metadata) and \
           not ROCRATE_FILENAME_PATTERN.match(metadata['name']):
            logger.debug(f'Generating file metadata: {action}, {metadata}')
            self._generate_draft_metadata(metadata, auth)
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='weko')
        self.owner.add_log(
            'weko_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.index_title,
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def create_waterbutler_deposit_log(self, auth, action, metadata):
        self.owner.add_log(
            'weko_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.index_title,
                'filename': metadata['materialized'].strip('/'),
                'path': metadata['materialized'],
                'urls': {
                    'view': metadata['item_html_url'],
                },
            },
        )

    def validate_index_id(self, index_id):
        if self.index_id == index_id:
            return True
        try:
            index = self.create_client().get_index_by_id(self.index_id)
        except (ValueError, IOError):
            logger.exception('Index validation failed')
            return False
        return self._validate_index_id(index, index_id)

    def get_metadata_repository(self):
        return {
            'metadata': {
                'provider': SHORT_NAME,
                'urls': {
                    'get': self.owner.api_url_for('weko_get_file_metadata'),
                },
                'permissions': {
                    'provider': False,
                },
            },
            'registries': [],
        }

    def get_metadata_destinations(self, schemas):
        r = []
        client = self.create_client()
        index = client.get_index_by_id(self.index_id)
        for schema in schemas:
            r += self._as_destinations(schema._id, index, '')
        return r

    def get_default_provider(self):
        addon = self.owner.get_addon('osfstorage')
        if addon.complete:
            return addon
        for addon in self.owner.get_addons():
            if not addon.complete:
                continue
            if addon.short_name not in website_settings.ADDONS_AVAILABLE_DICT:
                continue
            config = website_settings.ADDONS_AVAILABLE_DICT[addon.short_name]
            if config.for_institutions:
                return addon
        raise IOError('No default or institutional storages')

    def _validate_index_id(self, index, index_id):
        if index.identifier == index_id:
            return True
        for child in index.children:
            if self._validate_index_id(child, index_id):
                return True
        return False

    def _as_destinations(self, schema_id, index, parent):
        url = self.owner.api_url_for(
            'weko_publish_registration',
            index_id=index.identifier,
            registration_id='<reg>'
        )
        logger.info(f'URL: {url}')
        url = url[:url.index('/%3Creg%3E')]
        r = [
            {
                'id': 'weko-' + schema_id + '-' + index.identifier,
                'name': f'{FULL_NAME} ({parent}{index.title})',
                'url': url,
                'schema_id': schema_id,
                'acceptable': ['registration'],
            },
        ]
        url = self.owner.api_url_for(
            'weko_publish_draft_registration',
            index_id=index.identifier,
            draft_registration_id='<reg>'
        )
        url = url[:url.index('/%3Creg%3E')]
        r += [
            {
                'id': 'weko-' + schema_id + '-' + index.identifier + '-draft',
                'name': f'{FULL_NAME} ({parent}{index.title})',
                'url': url,
                'schema_id': schema_id,
                'acceptable': ['draft_registration'],
            },
        ]
        for child in index.children:
            r += self._as_destinations(schema_id, child, parent + index.title + ' > ')
        return r

    def _is_top_level_draft(self, metadata):
        extra = metadata.get('extra', None)
        if not extra:
            return False
        source = extra.get('source', None)
        if not source:
            return False
        path = source.get('materialized_path', None)
        if not path:
            return False
        return re.match(r'^\/\.weko\/[^\/]+\/[^\/]+\/?$', path)

    ##### Callback overrides #####

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def _generate_draft_metadata(self, metadata, auth):
        metadata_addon = self.owner.get_addon(METADATA_SHORT_NAME)
        if metadata_addon is None:
            logger.warn('Metadata addon is not configured')
            return None
        # NOOP
        return None

    def _clean_expired_publish_tasks(self):
        q = self.publish_task.filter(
            updated__lt=datetime.now() - timedelta(seconds=settings.PUBLISH_TASK_EXPIRATION),
        )
        q.delete()


class RegistrationMetadataMapping(BaseModel):
    registration_schema_id = models.CharField(max_length=64, blank=True, null=True)

    rules = DateTimeAwareJSONField(default=dict, blank=True)


class PublishTask(BaseModel):
    project = models.ForeignKey(NodeSettings, related_name='publish_task',
                                db_index=True, null=True, blank=True,
                                on_delete=models.CASCADE)

    path = models.TextField()

    updated = NonNaiveDateTimeField(blank=True, null=True)

    last_task_id = models.CharField(max_length=128, blank=True, null=True)


@receiver(post_save, sender=NodeLog)
def node_post_save(sender, instance, created, **kwargs):
    action = instance.action
    logger.debug(f'create_waterbutler_log: {action}, created={created}')
    if not created:
        return
    if action not in ['addon_file_moved', 'addon_file_copied']:
        return
    params = instance.params
    dest = params.get('destination', None)
    if not dest:
        return
    if dest.get('provider', None) != SHORT_NAME:
        return
    node = instance.node
    addon = node.get_addon(SHORT_NAME)
    if addon is None:
        return
    if not addon._is_top_level_draft(dest):
        logger.debug(f'Destination is not top level draft: {dest}')
        return
    logger.debug(f'Generating file metadata: {action}, {dest}')
    auth = Auth(user=instance.user)
    addon._generate_draft_metadata(dest, auth)
