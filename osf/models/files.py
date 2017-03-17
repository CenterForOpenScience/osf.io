import logging
import os

import requests
from dateutil.parser import parse as parse_date
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Manager
from django.utils import timezone
from modularodm.exceptions import NoResultsFound
from typedmodels.models import TypedModel

from framework.analytics import get_basic_counters
from osf.models.base import BaseModel, OptionalGuidMixin, ObjectIDMixin
from osf.models.comment import CommentableMixin
from osf.models.validators import validate_location
from osf.modm_compat import Q
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from website.files import utils
from website.files.exceptions import VersionNotFoundError
from website.util import api_v2_url, waterbutler_api_url_for

__all__ = (
    'File',
    'Folder',
    'FileVersion',
    'StoredFileNode',
    'TrashedFileNode',
)

PROVIDER_MAP = {}
logger = logging.getLogger(__name__)


class BaseFileNodeManager(Manager):
    def get_queryset(self):
        qs = super(BaseFileNodeManager, self).get_queryset()
        try:
            return qs.filter(provider=self.model._provider)
        except AttributeError:
            return qs


class BaseFileNode(TypedModel, CommentableMixin, OptionalGuidMixin, ObjectIDMixin, BaseModel):
    """
        The storage backend for FileNode objects.
        This class should generally not be used or created manually as FileNode
        contains all the helpers required.
        A FileNode wraps a StoredFileNode to provider usable abstraction layer
    """
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.base.StoredFileNode'
    modm_query = None
    migration_page_size = 10000
    # /TODO DELETE ME POST MIGRATION]
    version_identifier = 'revision'  # For backwards compatibility

    # The User that has this file "checked out"
    # Should only be used for OsfStorage
    checkout = models.ForeignKey('osf.OSFUser', blank=True, null=True)
    # The last time the touch method was called on this FileNode
    last_touched = NonNaiveDateTimeField(null=True, blank=True)
    # A list of dictionaries sorted by the 'modified' key
    # The raw output of the metadata request deduped by etag
    # Add regardless it can be pinned to a version or not
    history = DateTimeAwareJSONField(default=[], blank=True)
    # A concrete version of a FileNode, must have an identifier
    versions = models.ManyToManyField('FileVersion')

    node = models.ForeignKey('osf.AbstractNode', blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, default=None, related_name='child')
    copied_from = models.ForeignKey('self', blank=True, null=True, default=None, related_name='copy_of')

    provider = models.CharField(max_length=25, blank=False, null=False, db_index=True)

    name = models.TextField(blank=True, null=True)
    _path = models.TextField(blank=True, null=True)  # 1950 on prod
    _materialized_path = models.TextField(blank=True, null=True)  # 482 on staging

    is_deleted = False
    deleted_on = NonNaiveDateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey('osf.OSFUser', related_name='files_deleted_by', null=True, blank=True)

    objects = BaseFileNodeManager()

    class Meta:
        index_together = (
            ('node', 'type', 'provider', '_path'),
            ('node', 'type', 'provider'),
        )

    def to_storage(self):
        storage = super(BaseFileNode, self).to_storage()
        if 'trashed' not in self.type.lower():
            for key in tuple(storage.keys()):
                if 'deleted' in key:
                    storage.pop(key)
        return storage

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
        return waterbutler_api_url_for(
            self.node._id,
            self.provider,
            self.path,
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
            self.generate_waterbutler_url(revision=revision, meta=True, **kwargs),
            headers=headers,
        )
        if resp.status_code != 200:
            logger.warning('Unable to find {} got status code {}'.format(self, resp.status_code))
            return None
        return self.update(revision, resp.json()['data']['attributes'])
        # TODO Switch back to head requests
        # return self.update(revision, json.loads(resp.headers['x-waterbutler-metadata']))

    def update(self, revision, data, user=None):
        """Using revision and data update all data pretaining to self
        :param str or None revision: The revision that data points to
        :param dict data: Metadata recieved from waterbutler
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
            self.versions.add(version)
        for entry in self.history:
            if ('etag' in entry and 'etag' in data) and (entry['etag'] == data['etag']):
                break
        else:
            # Insert into history if there is no matching etag
            utils.insort(self.history, data, lambda x: x['modified'])

        # Finally update last touched
        self.last_touched = timezone.now()

        self.save()
        return version

    def get_download_count(self, version=None):
        """Pull the download count from the pagecounter collection
        Limit to version if specified.
        Currently only useful for OsfStorage
        """
        parts = ['download', self.node._id, self._id]
        if version is not None:
            parts.append(version)
        page = ':'.join([format(part) for part in parts])
        _, count = get_basic_counters(page)

        return count or 0

    @property
    def is_file(self):
        # TODO split is file logic into subclasses
        return issubclass(self.__class__, (File, TrashedFile))

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
        return self.node.web_url_for('addon_view_or_download_file', provider=self.provider, path=self.path.strip('/'))

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

    def belongs_to_node(self, node_id):
        """Check whether the file is attached to the specified node."""
        return self.node._id == node_id

    def get_extra_log_params(self, comment):
        return {'file': {'name': self.name, 'url': comment.get_comment_page_url()}}

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def wrapped(self):
        """Wrap self in a FileNode subclass
        """
        raise Exception('Wrapped is deprecated.')

    def save(self, *args, **kwargs):
        if hasattr(self._meta.model, '_provider'):
            self.provider = self._meta.model._provider
        super(BaseFileNode, self).save(*args, **kwargs)

    @classmethod
    def create(cls, **kwargs):
        kwargs.update(provider=cls._provider)
        return cls(**kwargs)

    @classmethod
    def get_or_create(cls, node, path):
        obj, _ = cls.objects.get_or_create(node=node, _path='/' + path.lstrip('/'))
        return obj

    @classmethod
    def get_file_guids(cls, materialized_path, provider, node):
        guids = []
        materialized_path = '/' + materialized_path.lstrip('/')
        if materialized_path.endswith('/'):
            # it's a folder
            folder_children = cls.find(Q('provider', 'eq', provider) &
                                       Q('node', 'eq', node) &
                                       Q('_materialized_path', 'startswith', materialized_path))
            for item in folder_children:
                if item.kind == 'file':
                    guid = item.get_guid()
                    if guid:
                        guids.append(guid._id)
        else:
            # it's a file
            try:
                file_obj = cls.find_one(
                    Q('node', 'eq', node) & Q('_materialized_path', 'eq', materialized_path))
            except NoResultsFound:
                return guids
            guid = file_obj.get_guid()
            if guid:
                guids.append(guid._id)

        return guids


# TODO Refactor code pointing at FileNode to point to StoredFileNode
FileNode = StoredFileNode = BaseFileNode


class File(models.Model):
    _is_file = True

    class Meta:
        abstract = True

    @property
    def kind(self):
        return 'file'

    def serialize(self):
        if not self.versions.exists():
            return dict(
                super(File, self).serialize(),
                size=None,
                version=None,
                modified=None,
                created=None,
                contentType=None,
                downloads=self.get_download_count(),
                checkout=self.checkout._id if self.checkout else None,
            )

        version = self.versions.all()[-1]
        return dict(
            super(File, self).serialize(),
            size=version.size,
            downloads=self.get_download_count(),
            checkout=self.checkout._id if self.checkout else None,
            version=version.identifier if self.versions else None,
            contentType=version.content_type if self.versions else None,
            modified=version.date_modified.isoformat() if version.date_modified else None,
            created=self.versions[0].date_modified.isoformat() if self.versions[0].date_modified else None,
        )

    def restore(self, recursive=True, parent=None, save=True, deleted_on=None):
        raise Exception('You cannot restore something that is not deleted.')

    def delete(self, user=None, parent=None, save=True, deleted_on=None):
        """
        Recast a File into TrashedFile and set fields related to deleting.
        :param user:
        :param parent:
        :param save:
        :param deleted_on:
        :return:
        """
        self.recast(TrashedFile._typedmodels_type)
        self.deleted_by = user
        self.deleted_on = deleted_on = deleted_on or timezone.now()

        if save:
            self.save()

        return self
    # TODO Which serializer is right?
    # def serialize(self, **kwargs):
    #     return {
    #         'id': self._id,
    #         'path': self.path,
    #         'name': self.name,
    #         'kind': self.kind,
    #     }


class Folder(models.Model):
    _is_file = False

    class Meta:
        abstract = True

    def delete(self, user=None, parent=None, save=True, deleted_on=None):
        """
        Recast a Folder to TrashedFolder, set fields related to deleting,
        and recast children.
        :param user:
        :param parent:
        :param save:
        :param deleted_on:
        :return:
        """
        self.recast(TrashedFolder._typedmodels_type)
        self.deleted_by = user
        self.deleted_on = deleted_on = deleted_on or timezone.now()

        if save:
            self.save()

        if not self.is_file:
            for child in BaseFileNode.objects.filter(parent=self.id).exclude(type__icontains='trashed'):
                child.delete(user=user, save=save, deleted_on=deleted_on)
        return self

    @property
    def kind(self):
        return 'folder'

    @property
    def children(self):
        """Finds all Filenodes that view self as a parent
        :returns: A GenWrapper for all children
        :rtype: GenWrapper<MongoQuerySet<cls>>
        """
        return FileNode.find(Q('parent_id', 'eq', self.id))

    # def delete(self, recurse=True, user=None, parent=None):
    #     trashed = self._create_trashed(user=user, parent=parent)
    #     if recurse:
    #         for child in self.children:
    #             child.delete(user=user, parent=trashed)
    #     self._repoint_guids(trashed)
    #     StoredFileNode.remove_one(self.stored_object)
    #     return trashed

    def append_file(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, File, path=path, materialized_path=materialized_path, save=save)

    def append_folder(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, Folder, path=path, materialized_path=materialized_path, save=save)

    def _create_child(self, name, kind, path=None, materialized_path=None, save=True):
        child = self._resolve_class(kind)(
            name=name,
            node=self.node,
            path=path or '/' + name,
            parent=self,
            materialized_path=materialized_path or
            os.path.join(self.materialized_path, name) + '/' if kind is Folder else ''
        )
        if save:
            child.save()
        return child

    def find_child_by_name(self, name, kind=2):
        # kind == 2
        type_cls = None
        if kind == 1:
            # file
            type_cls = File
        elif kind == 0:
            # folder
            type_cls = Folder
        return self._resolve_class(type_cls).find_one(
            Q('name', 'eq', name) &
            Q('parent', 'eq', self)
        )


class TrashedFileNode(BaseFileNode):
    is_deleted = True

    def delete(self, user=None, parent=None, save=True, deleted_on=None):
        if isinstance(self, TrashedFileNode):
            raise Exception('You cannot delete things that are deleted.')

    def restore(self, recursive=True, parent=None, save=True, deleted_on=None):
        """
        Restore a file or folder
        :param recursive:
        :param parent:
        :param save:
        :param deleted_on:
        :return:
        """
        type_cls = File if self.is_file else Folder

        self.recast(self._resolve_class(type_cls)._typedmodels_type)

        if save:
            self.save()

        if self.parent and self.parent.is_deleted:
            raise ValueError('No parent to restore to')

        return self


class TrashedFile(TrashedFileNode):
    @property
    def kind(self):
        return 'file'


class TrashedFolder(TrashedFileNode):
    @property
    def kind(self):
        return 'folder'

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


class FileVersion(ObjectIDMixin, BaseModel):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """

    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.base.FileVersion'
    modm_query = None
    migration_page_size = 100000
    # /TODO DELETE ME POST MIGRATION

    creator = models.ForeignKey('OSFUser', null=True, blank=True)

    identifier = models.CharField(max_length=100, blank=False, null=False)  # max length on staging was 51

    # Date version record was created. This is the date displayed to the user.
    date_created = NonNaiveDateTimeField(default=timezone.now)  # auto_now_add=True)

    size = models.BigIntegerField(default=-1, blank=True)

    content_type = models.CharField(max_length=100, blank=True, null=True)  # was 24 on staging
    # Date file modified on third-party backend. Not displayed to user, since
    # this date may be earlier than the date of upload if the file already
    # exists on the backend
    date_modified = NonNaiveDateTimeField(null=True, blank=True)

    metadata = DateTimeAwareJSONField(blank=True, default=dict)
    location = DateTimeAwareJSONField(default=None, blank=True, null=True, validators=[validate_location])

    @property
    def location_hash(self):
        return self.location['object']

    @property
    def archive(self):
        return self.metadata.get('archive')

    def is_duplicate(self, other):
        return self.location_hash == other.location_hash

    def update_metadata(self, metadata, save=True):
        self.metadata.update(metadata)
        # metadata has no defined structure so only attempt to set attributes
        # If its are not in this callback it'll be in the next
        self.size = self.metadata.get('size', self.size)
        self.content_type = self.metadata.get('contentType', self.content_type)
        if self.metadata.get('modified'):
            self.date_modified = parse_date(self.metadata['modified'], ignoretz=False)

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

        qs = self.__class__.find(
            Q('_id', 'ne', self._id) &
            Q('metadata.vault', 'ne', None) &
            Q('metadata.archive', 'ne', None) &
            Q('metadata.sha256', 'eq', self.metadata['sha256'])
        ).limit(1)
        if qs.count() < 1:
            return False
        other = qs[0]
        try:
            self.metadata['vault'] = other.metadata['vault']
            self.metadata['archive'] = other.metadata['archive']
        except KeyError:
            return False
        if save:
            self.save()
        return True

    class Meta:
        ordering = ('date_created',)
