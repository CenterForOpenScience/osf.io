from __future__ import unicode_literals

import logging
import os

import requests
from dateutil.parser import parse as parse_date
from django.apps import apps
from django.db import models, IntegrityError
from django.db.models import Manager
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from typedmodels.models import TypedModel, TypedModelManager
from include import IncludeManager

from framework.analytics import get_basic_counters
from framework import sentry
from osf.models.base import BaseModel, OptionalGuidMixin, ObjectIDMixin
from osf.models.comment import CommentableMixin
from osf.models.mixins import Taggable
from osf.models.validators import validate_location
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from api.base.utils import waterbutler_api_url_for
from website.files import utils
from website.files.exceptions import VersionNotFoundError
from website.util import api_v2_url, web_url_for, api_url_for

__all__ = (
    'File',
    'Folder',
    'FileVersion',
    'BaseFileNode',
    'TrashedFileNode',
)

PROVIDER_MAP = {}
logger = logging.getLogger(__name__)


class BaseFileNodeManager(TypedModelManager, IncludeManager):

    def get_queryset(self):
        qs = super(BaseFileNodeManager, self).get_queryset()

        if hasattr(self.model, '_provider') and self.model._provider is not None:
            return qs.filter(provider=self.model._provider)
        return qs

class ActiveFileNodeManager(Manager):
    """Manager that filters out TrashedFileNodes.
    Note: We do not use this as the default manager for BaseFileNode because
    that would prevent TrashedFileNodes from accessing their `parent` field if
    the parent was not a TrashedFileNode.

    WARNING: Do NOT use .active on BaseFileNode subclasses. Use .objects instead.
    """

    def get_queryset(self):
        qs = super(ActiveFileNodeManager, self).get_queryset()
        return qs.exclude(type__in=TrashedFileNode._typedmodels_subtypes)

class UnableToResolveFileClass(Exception):
    pass


class BaseFileNode(TypedModel, CommentableMixin, OptionalGuidMixin, Taggable, ObjectIDMixin, BaseModel):
    """Base class for all provider-specific file models and the trashed file model.
    This class should generally not be used or created manually. Use the provider-specific
    subclasses instead.

    WARNING: Be careful when using ``.filter``, ``.exclude``, etc. on this model.
    The default queryset for will NOT filter out TrashedFileNodes by default.
    Also, calling ``.load`` may return a `TrashedFileNode`.
    Use the ``BaseFileNode.active`` manager when you want to filter out TrashedFileNodes.
    """
    version_identifier = 'revision'  # For backwards compatibility
    FOLDER, FILE, ANY = 0, 1, 2

    # The User that has this file "checked out"
    # Should only be used for OsfStorage
    checkout = models.ForeignKey('osf.OSFUser', blank=True, null=True, on_delete=models.CASCADE)
    # The last time the touch method was called on this FileNode
    last_touched = NonNaiveDateTimeField(null=True, blank=True)
    # A list of dictionaries sorted by the 'modified' key
    # The raw output of the metadata request deduped by etag
    # Add regardless it can be pinned to a version or not
    _history = DateTimeAwareJSONField(default=list, blank=True)
    # A concrete version of a FileNode, must have an identifier
    versions = models.ManyToManyField('FileVersion', through='BaseFileVersionsThrough')

    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey('target_content_type', 'target_object_id')

    parent = models.ForeignKey('self', blank=True, null=True, default=None, related_name='_children', on_delete=models.CASCADE)
    copied_from = models.ForeignKey('self', blank=True, null=True, default=None, related_name='copy_of', on_delete=models.CASCADE)

    provider = models.CharField(max_length=25, blank=False, null=False, db_index=True)

    name = models.TextField(blank=True)
    _path = models.TextField(blank=True, null=True)  # 1950 on prod
    _materialized_path = models.TextField(blank=True, null=True)  # 482 on staging

    is_deleted = False
    deleted_on = NonNaiveDateTimeField(blank=True, null=True)
    deleted = NonNaiveDateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey('osf.OSFUser', related_name='files_deleted_by', null=True, blank=True, on_delete=models.CASCADE)
    # Deleted in application and removed from cloud storage
    purged = NonNaiveDateTimeField(blank=True, null=True)

    objects = BaseFileNodeManager()
    active = ActiveFileNodeManager()

    class Meta:
        base_manager_name = 'objects'
        index_together = (
            ('target_content_type', 'target_object_id', )
        )

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, value):
        setattr(self, '_history', value)

    @property
    def is_file(self):
        # TODO split is file logic into subclasses
        return isinstance(self, (File, TrashedFile))

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def materialized_path(self):
        return self._materialized_path

    @materialized_path.setter
    def materialized_path(self, val):
        self._materialized_path = val

    @property
    def deep_url(self):
        """The url that this filenodes guid should resolve to.
        Implemented here so that subclasses may override it or path.
        See OsfStorage or PathFollowingNode.
        """
        # Files are inaccessible if a node is retracted, so just show
        # the retraction detail page for files on retractions
        from osf.models import AbstractNode
        if isinstance(self.target, AbstractNode):
            if self.target.is_registration and self.target.is_retracted:
                return self.target.web_url_for('view_project')
        return web_url_for('addon_view_or_download_file', guid=self.target._id, provider=self.provider, path=self.path.strip('/'))

    @property
    def absolute_api_v2_url(self):
        path = '/files/{}/'.format(self._id)
        return api_v2_url(path)

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'files'

    @property
    def root_target_page(self):
        """The comment page type associated with StoredFileNodes."""
        return 'files'

    @property
    def current_version_number(self):
        if self.history:
            return len(self.history)
        return 1

    @classmethod
    def create(cls, **kwargs):
        kwargs.update(provider=cls._provider)
        return cls(**kwargs)

    @classmethod
    def get_or_create(cls, target, path):
        content_type = ContentType.objects.get_for_model(target)
        try:
            obj = cls.objects.get(target_object_id=target.id, target_content_type=content_type, _path='/' + path.lstrip('/'))
        except cls.DoesNotExist:
            obj = cls(target_object_id=target.id, target_content_type=content_type, _path='/' + path.lstrip('/'))
        return obj

    @classmethod
    def get_file_guids(cls, materialized_path, provider, target):
        content_type = ContentType.objects.get_for_model(target)
        guids = []
        materialized_path = '/' + materialized_path.lstrip('/')
        if materialized_path.endswith('/'):
            # it's a folder
            folder_children = cls.objects.filter(provider=provider, target_object_id=target.id, target_content_type=content_type, _materialized_path__startswith=materialized_path)
            for item in folder_children:
                if item.kind == 'file':
                    guid = item.get_guid()
                    if guid:
                        guids.append(guid._id)
        else:
            # it's a file
            try:
                file_obj = cls.objects.get(
                    target_object_id=target.id, target_content_type=content_type, _materialized_path=materialized_path
                )
            except cls.DoesNotExist:
                return guids
            guid = file_obj.get_guid()
            if guid:
                guids.append(guid._id)

        return guids

    def has_permission(self, user, perm):
        return self.node and self.node.has_permission(user, perm)

    def to_storage(self, **kwargs):
        storage = super(BaseFileNode, self).to_storage(**kwargs)
        if 'trashed' not in self.type.lower():
            for key in tuple(storage.keys()):
                if 'deleted' in key:
                    storage.pop(key)
        return storage

    def add_version(self, version, name=None):
        """
        Relates the file object to the version object.
        :param version: Version object
        :param name: Name, optional.  Pass in if this version needs to have
        a different name than the file
        :return: Returns version that was passed in
        """
        version_name = name or self.name
        BaseFileVersionsThrough.objects.create(fileversion=version, basefilenode=self, version_name=version_name)
        return version

    @classmethod
    def files_checked_out(cls, user):
        """
        :param user: The user with checked out files
        :return: A queryset of all FileNodes checked out by user
        """
        return cls.objects.filter(checkout=user)

    @classmethod
    def resolve_class(cls, provider, type_integer):
        type_mapping = {0: Folder, 1: File, 2: None}
        type_cls = type_mapping[type_integer]

        for subclass in BaseFileNode.__subclasses__():
            if type_cls:
                for subsubclass in subclass.__subclasses__():
                    if issubclass(subsubclass, type_cls) and subsubclass._provider == provider:
                        return subsubclass
            else:
                if subclass._provider == provider:
                    return subclass
        raise UnableToResolveFileClass('Could not resolve class for {} and {}'.format(provider, type_cls))

    def _resolve_class(self, type_cls):
        for subclass in BaseFileNode.__subclasses__():
            if type_cls:
                for subsubclass in subclass.__subclasses__():
                    if issubclass(subsubclass, type_cls) and subsubclass._provider == self.provider:
                        return subsubclass
            else:
                if subclass._provider == self.provider:
                    return subclass

    def get_version(self, revision, required=False):
        """Find a version with identifier revision
        :returns: FileVersion or None
        :raises: VersionNotFoundError if required is True
        """
        try:
            return self.versions.get(identifier=revision)
        except ObjectDoesNotExist:
            if required:
                raise VersionNotFoundError(revision)
            return None

    def generate_waterbutler_url(self, **kwargs):
        base_url = None
        if hasattr(self.target, 'osfstorage_region'):
            base_url = self.target.osfstorage_region.waterbutler_url
        return waterbutler_api_url_for(
            self.target._id,
            self.provider,
            self.path,
            base_url=base_url,
            **kwargs
        )

    def update_version_metadata(self, location, metadata):
        try:
            self.versions.get(location=location).update_metadata(metadata)
            return
        except ObjectDoesNotExist:
            raise VersionNotFoundError(location)

    def touch(self, auth_header, revision=None, **kwargs):
        """The bread and butter of File, collects metadata about self
        and creates versions and updates self when required.
        If revisions is None the created version is NOT and should NOT be saved
        as there is no identifing information to tell if it needs to be updated or not.
        Hits Waterbutler's metadata endpoint and saves the returned data.
        If a file cannot be rendered IE figshare private files a tuple of the FileVersion and
        renderable HTML will be returned.
            >>>isinstance(file_node.touch(), tuple) # This file cannot be rendered
        :param str or None auth_header: If truthy it will set as the Authorization header
        :returns: None if the file is not found otherwise FileVersion or (version, Error HTML)
        """
        # Resvolve primary key on first touch
        self.save()
        # For backwards compatibility
        revision = revision or kwargs.get(self.version_identifier)

        version = self.get_version(revision)
        # Versions do not change. No need to refetch what we already know
        if version is not None:
            return version

        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header

        resp = requests.get(
            self.generate_waterbutler_url(revision=revision, meta=True, _internal=True, **kwargs),
            headers=headers,
        )
        if resp.status_code != 200:
            logger.warning('Unable to find {} got status code {}'.format(self, resp.status_code))
            return None
        return self.update(revision, resp.json()['data']['attributes'])
        # TODO Switch back to head requests
        # return self.update(revision, json.loads(resp.headers['x-waterbutler-metadata']))

    def get_page_counter_count(self, count_type, version=None):
        """Assembles a string to retrieve the correct file data from the pagecounter collection,
        then calls get_basic_counters to retrieve the total count. Limit to version if specified.
        """
        _, count = get_basic_counters(self.target.guids.first(), self, version=version, action=count_type)

        return count or 0

    def get_download_count(self, version=None):
        """Pull the download count from the pagecounter collection"""
        return self.get_page_counter_count('download', version=version)

    def get_view_count(self, version=None):
        """Pull the mfr view count from the pagecounter collection"""
        return self.get_page_counter_count('view', version=version)

    def copy_under(self, destination_parent, name=None):
        return utils.copy_files(self, destination_parent.target, destination_parent, name=name)

    def move_under(self, destination_parent, name=None):
        renaming = name != self.name
        self.name = name or self.name
        self.parent = destination_parent
        self._update_node(save=True)  # Trust _update_node to save us

        if renaming and self.is_file and self.versions.exists():
            newest_version = self.versions.first()
            node_file_version = newest_version.get_basefilenode_version(self)
            # Rename version in through table
            node_file_version.version_name = self.name
            node_file_version.save()

        return self

    def belongs_to_node(self, target_id):
        """Check whether the file is attached to the specified node."""
        return self.target._id == target_id

    def get_extra_log_params(self, comment):
        return {'file': {'name': self.name, 'url': comment.get_comment_page_url()}}

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_absolute_info_url(self):
        return self.absolute_api_v2_url

    def _repoint_guids(self, updated):
        logger.warn('BaseFileNode._repoint_guids is deprecated.')

    def _update_node(self, recursive=True, save=True):
        if self.parent is not None:
            self.target = self.parent.target
        if save:
            self.save()
        if recursive and not self.is_file:
            for child in self.children:
                child._update_node(save=save)

    def delete(self, user=None, save=True, deleted_on=None):
        """
        Recast a Folder to TrashedFolder, set fields related to deleting,
        and recast children.
        :param user:
        :param save:
        :param deleted_on:
        :return:
        """
        deleted = deleted_on
        if not self.is_root:
            self.deleted_by = user
            self.deleted = deleted_on or timezone.now()
            deleted = self.deleted
            # This will need to be removed
            self.deleted_on = deleted

        if not self.is_file:
            if not self.is_root:
                self.recast(TrashedFolder._typedmodels_type)

            for child in BaseFileNode.objects.filter(parent=self.id).exclude(type__in=TrashedFileNode._typedmodels_subtypes):
                child.delete(user=user, save=save, deleted_on=deleted)
        else:
            self.recast(TrashedFile._typedmodels_type)

            guid = self.guids.first()
            if guid:
                Comment = apps.get_model('osf.Comment')
                Comment.objects.filter(root_target=guid).update(root_target=None)

        if save:
            self.save()

        return self

    def _serialize(self, **kwargs):
        return {
            'id': self._id,
            'path': self.path,
            'name': self.name,
            'kind': self.kind,
        }

    def save(self, *args, **kwargs):
        if hasattr(self._meta.model, '_provider') and self._meta.model._provider is not None:
            self.provider = self._meta.model._provider
        super(BaseFileNode, self).save(*args, **kwargs)

    def __repr__(self):
        return '<{}(name={!r}, target={!r})>'.format(
            self.__class__.__name__,
            self.name,
            self.target
        )


class UnableToRestore(Exception):
    pass


class File(models.Model):
    class Meta:
        abstract = True

    @property
    def kind(self):
        return 'file'

    def update(self, revision, data, user=None, save=True):
        """Using revision and data update all data pretaining to self
        :param str or None revision: The revision that data points to
        :param dict data: Metadata received from waterbutler
        :returns: FileVersion
        """
        self.name = data['name']
        self.materialized_path = data['materialized']

        version = FileVersion(identifier=revision)
        version.update_metadata(data, save=False)

        # Transform here so it can be sortted on later
        if data['modified'] is not None and data['modified'] != '':
            data['modified'] = parse_date(
                data['modified'],
                ignoretz=True,
                default=timezone.now()  # Just incase nothing can be parsed
            )

        # if revision is none then version is the latest version
        # Dont save the latest information
        if revision is not None:
            version.save()
            # Adds version to the list of file versions - using custom through table
            self.add_version(version)
        for entry in self.history:
            # Some entry might have an undefined modified field
            if data['modified'] is not None and entry['modified'] is not None and data['modified'] < entry['modified']:
                sentry.log_message('update() receives metatdata older than the newest entry in file history.')
            if ('etag' in entry and 'etag' in data) and (entry['etag'] == data['etag']):
                break
        else:
            self.history.append(data)

        # Finally update last touched
        self.last_touched = timezone.now()

        if save:
            self.save()
        return version

    def serialize(self):
        newest_version = self.versions.all().last()

        if not newest_version:
            return dict(self._serialize(), **{
                'size': None,
                'version': None,
                'modified': None,
                'created': None,
                'contentType': None,
                'downloads': self.get_download_count(),
                'checkout': self.checkout._id if self.checkout else None,
            })

        return dict(self._serialize(), **{
            'size': newest_version.size,
            'downloads': self.get_download_count(),
            'checkout': self.checkout._id if self.checkout else None,
            'version': newest_version.identifier if newest_version else None,
            'contentType': newest_version.content_type if newest_version else None,
            'modified': newest_version.external_modified.isoformat() if newest_version.external_modified else None,
            'created': self.versions.all().first().external_modified.isoformat() if self.versions.all().first().external_modified else None,
        })

    def restore(self, recursive=True, parent=None, save=True, deleted_on=None):
        raise UnableToRestore('You cannot restore something that is not deleted.')

    @property
    def last_known_metadata(self):
        try:
            last_history = self._history[-1]
        except IndexError:
            size = None
        else:
            size = last_history.get('size', None)
        return {
            'path': self._materialized_path,
            'hashes': self._hashes,
            'size': size,
            'last_seen': self.last_touched
        }

    @property
    def _hashes(self):
        """ Hook for sublasses to return file hashes, commit SHAs, etc.
        Returns dict or None
        """
        return None

class Folder(models.Model):

    class Meta:
        abstract = True

    @property
    def kind(self):
        return 'folder'

    @property
    def children(self):
        return self._children.exclude(type__in=TrashedFileNode._typedmodels_subtypes)

    def update(self, revision, data, save=True, user=None):
        """Note: User is a kwargs here because of special requirements of
        dataverse and django
        See dataversefile.update
        """
        self.name = data['name']
        self.materialized_path = data['materialized']
        self.last_touched = timezone.now()
        if save:
            self.save()

    def append_file(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, File, path=path, materialized_path=materialized_path, save=save)

    def append_folder(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, Folder, path=path, materialized_path=materialized_path, save=save)

    def _create_child(self, name, kind, path=None, materialized_path=None, save=True):
        if not self.pk:
            logger.warn('BaseFileNode._create_child caused an implicit save because you just created a child with an unsaved parent.')
            self.save()

        target_content_type = ContentType.objects.get_for_model(self.target)
        if self._resolve_class(kind).objects.filter(
            name=name,
            target_object_id=self.target.id,
            target_content_type=target_content_type,
            parent=self
        ).exists():
            raise IntegrityError('Child by that name already, exists, update instead')
        else:
            child = self._resolve_class(kind)(
                name=name,
                target=self.target,
                path=path or '/' + name,
                parent=self,
                materialized_path=materialized_path or
                os.path.join(self.materialized_path, name) + '/' if kind is Folder else ''
            )
        if save:
            child.save()
        return child

    def find_child_by_name(self, name, kind=2):
        return self.resolve_class(self.provider, kind).objects.get(name=name, parent=self)

    def serialize(self):
        return self._serialize()


class UnableToDelete(Exception):
    pass


class TrashedFileNode(BaseFileNode):
    is_deleted = True
    _provider = None

    def delete(self, user=None, save=True, deleted_on=None):
        if isinstance(self, TrashedFileNode):  # TODO Why is this needed
            raise UnableToDelete('You cannot delete things that are deleted.')

    def restore(self, recursive=True, parent=None, save=True, deleted_on=None, client=None):
        """
        Restore a file or folder
        :param recursive:
        :param parent:
        :param save:
        :param deleted_on:
        :param client:
        :return:
        """
        if self.parent and self.parent.is_deleted:
            raise ValueError('No parent to restore to')
        if self.purged and client:
            self._unpurge(client=client)

        type_cls = File if self.is_file else Folder

        self.recast(self._resolve_class(type_cls)._typedmodels_type)

        if save:
            self.save()

        return self

    def _purge(self, client=None, save=True):
        """ Never call this.
            Purges cloud storage.

            return: Bytes deleted
        """
        if not client:
            logger.warn(f'No GCS Client detected. Not purging BFN {self.id}')
            return 0
        freed = 0
        for version in self.versions.all():
            freed += version._purge(client=client, save=save)
        self.purged = timezone.now()
        if save:
            self.save()
        return freed

    def _unpurge(self, client=None, save=True):
        if not client:
            logger.warn(f'No GCS Client detected. Not unpurging BFN {self.id}')
            return 0
        consumed = self.versions.latest()._unpurge(client=client, save=save)
        self.purged = None
        if save:
            self.save()
        return consumed

class TrashedFile(TrashedFileNode):
    @property
    def kind(self):
        return 'file'

    @property
    def _hashes(self):
        last_version = self.versions.last()
        if not last_version:
            return None
        return {
            'sha1': last_version.metadata['sha1'],
            'sha256': last_version.metadata['sha256'],
            'md5': last_version.metadata['md5']
        }

    @property
    def last_known_metadata(self):
        last_version = self.versions.last()
        if not last_version:
            size = None
        else:
            size = last_version.size
        return {
            'path': self.materialized_path,
            'hashes': self._hashes,
            'size': size,
            'last_seen': self.modified
        }

class TrashedFolder(TrashedFileNode):
    @property
    def kind(self):
        return 'folder'

    @property
    def trashed_children(self):
        return self._children.filter(type__in=TrashedFileNode._typedmodels_subtypes)

    @property
    def children(self):
        return self.trashed_children

    def restore(self, recursive=True, parent=None, save=True, deleted_on=None):
        """
        Restore a folder
        :param recursive:
        :param parent:
        :param save:
        :param deleted_on:
        :return:
        """
        tf = super(TrashedFolder, self).restore(recursive=True, parent=None, save=True, deleted_on=None)

        if not self.is_file and recursive:
            deleted_on = deleted_on or self.deleted_on
            for child in TrashedFileNode.objects.filter(parent=self.id, deleted_on=deleted_on):
                child.restore(recursive=True, save=save, deleted_on=deleted_on)
        return tf


class FileVersionUserMetadata(BaseModel):
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    file_version = models.ForeignKey('FileVersion', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'file_version')


class FileVersion(ObjectIDMixin, BaseModel):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """
    # Note on fields:
    # `created`: Date version record was created. This is the date displayed to the user.
    # `modified`: Date this object was last modified. Distinct from the date the file associated
    #       with this object was last modified
    # `external_modified`: Date file modified on third-party backend. Not displayed to user, since
    #       this date may be earlier than the date of upload if the file already
    #       exists on the backend

    creator = models.ForeignKey('OSFUser', null=True, blank=True, on_delete=models.CASCADE)

    identifier = models.CharField(max_length=100, blank=False, null=False)  # max length on staging was 51

    size = models.BigIntegerField(default=-1, blank=True, null=True)

    content_type = models.CharField(max_length=100, blank=True, null=True)  # was 24 on staging
    external_modified = NonNaiveDateTimeField(null=True, blank=True)

    metadata = DateTimeAwareJSONField(blank=True, default=dict)
    location = DateTimeAwareJSONField(default=None, blank=True, null=True, validators=[validate_location])
    seen_by = models.ManyToManyField('OSFUser', through=FileVersionUserMetadata, related_name='versions_seen')
    region = models.ForeignKey('addons_osfstorage.Region', null=True, blank=True, on_delete=models.CASCADE)

    purged = NonNaiveDateTimeField(blank=True, null=True)

    includable_objects = IncludeManager()

    @property
    def location_hash(self):
        return self.location['object']

    @property
    def archive(self):
        return self.metadata.get('archive')

    def _purge(self, client=None, save=True):
        if not client:
            logger.warn(f'No GCS Client detected. Not purging FV {self.id}')
            return 0
        if self.basefilenode_set.filter(deleted__isnull=True).exists():
            logger.warn(f'Live file detected. Not purging FV {self.id}')
            return 0
        if not self.location or not self.location.get('object'):
            logger.warn(f'No valid location detected. Not purging FV {self.id}')
            return 0
        dup = FileVersion.objects.exclude(id=self.id).filter(location__object=self.location['object'], basefilenode__deleted__isnull=True).first()
        if dup:
            logger.warn(f'Duplicate live file detected on FV {dup.id}. Not purging FV {self.id}')
            return 0
        bucket = client.get_bucket(self.location['bucket'])
        blob = bucket.get_blob(self.location['object'])
        if blob:
            blob.delete()
        else:
            logger.warn(f'Blob not found for FV {self.id}. Marking as purged.')
        self.purged = timezone.now()
        if save:
            self.save()
        return self.size

    def _unpurge(self, client=None, save=True):
        if not self.purged:
            return 0
        if not client:
            logger.warn(f'No GCS Credentials detected. Not unpurging FV {self.id}')
            return 0
        backup_bucket = client.get_bucket('{}-backup'.format(self.location['bucket']))
        bucket = client.get_bucket(self.location['bucket'])
        blob = bucket.get_blob(self.location['object'])
        backup_bucket.copy_blob(blob, bucket)
        self.purged = None
        if save:
            self.save()
        return self.size

    def is_duplicate(self, other):
        return self.location_hash == other.location_hash

    def get_basefilenode_version(self, file):
        # Returns the throughtable object  - the record that links this version
        # to the given file.
        return self.basefileversionsthrough_set.filter(basefilenode=file).first()

    def update_metadata(self, metadata, save=True):
        self.metadata.update(metadata)
        # metadata has no defined structure so only attempt to set attributes
        # If its are not in this callback it'll be in the next
        self.size = self.metadata.get('size', self.size)
        self.content_type = self.metadata.get('contentType', self.content_type)
        if self.metadata.get('modified'):
            self.external_modified = parse_date(self.metadata['modified'], ignoretz=False)

        if save:
            self.save()

    def _find_matching_archive(self, save=True):
        """Find another version with the same sha256 as this file.
        If found copy its vault name and glacier id, no need to create additional backups.
        returns True if found otherwise false
        """

        if 'sha256' not in self.metadata:
            return False  # Dont bother searching for nothing

        if 'vault' in self.metadata and 'archive' in self.metadata:
            # Shouldn't ever happen, but we already have an archive
            return True  # We've found ourself

        other = self.__class__.objects.filter(
            metadata__sha256=self.metadata['sha256']
        ).exclude(
            _id=self._id, metadata__archive__is_null=True, metadata__vault__is_null=True
        )
        if not other.exists():
            return False
        try:
            other = other.first()
            self.metadata['vault'] = other.metadata['vault']
            self.metadata['archive'] = other.metadata['archive']
        except KeyError:
            return False
        if save:
            self.save()
        return True

    def serialize_waterbutler_settings(self, node_id, root_id):
        return dict(self.region.waterbutler_settings, **{
            'nid': node_id,
            'rootId': root_id,
            'baseUrl': api_url_for(
                'osfstorage_get_metadata',
                guid=node_id,
                _absolute=True,
                _internal=True
            ),
        })

    class Meta:
        ordering = ('-created',)


class BaseFileVersionsThrough(models.Model):
    basefilenode = models.ForeignKey(BaseFileNode, db_index=True, on_delete=models.CASCADE)
    fileversion = models.ForeignKey(FileVersion, db_index=True, on_delete=models.CASCADE)
    version_name = models.TextField(blank=True)

    class Meta:
        unique_together = (('basefilenode', 'fileversion'),)
        index_together = (
            ('basefilenode', 'fileversion', )
        )
