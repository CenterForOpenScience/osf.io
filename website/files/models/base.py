from __future__ import unicode_literals

import os
import bson
import logging
import pymongo
import datetime
import requests
import functools

from modularodm import fields, Q
from modularodm.exceptions import NoResultsFound
from dateutil.parser import parse as parse_date

from framework.guid.model import Guid
from framework.mongo import StoredObject
from framework.mongo.utils import unique_on
from framework.analytics import get_basic_counters

from website import util
from website.files import utils
from website.files import exceptions
from website.project.commentable import Commentable


__all__ = (
    'File',
    'Folder',
    'FileNode',
    'FileVersion',
    'StoredFileNode',
    'TrashedFileNode',
)


PROVIDER_MAP = {}
logger = logging.getLogger(__name__)


class TrashedFileNode(StoredObject, Commentable):
    """The graveyard for all deleted FileNodes"""

    __indices__ = [{
        'unique': False,
        'key_or_list': [
            ('node', pymongo.ASCENDING),
            ('is_file', pymongo.ASCENDING),
            ('provider', pymongo.ASCENDING),
        ]
    }]

    _id = fields.StringField(primary=True)

    last_touched = fields.DateTimeField()
    history = fields.DictionaryField(list=True)
    versions = fields.ForeignField('FileVersion', list=True)

    node = fields.ForeignField('node', required=True)
    parent = fields.AbstractForeignField(default=None)

    is_file = fields.BooleanField(default=True)
    provider = fields.StringField(required=True)

    name = fields.StringField(required=True)
    path = fields.StringField(required=True)
    materialized_path = fields.StringField(required=True)

    checkout = fields.AbstractForeignField('User')
    deleted_by = fields.AbstractForeignField('User')
    deleted_on = fields.DateTimeField(auto_now_add=True)
    tags = fields.ForeignField('Tag', list=True)
    suspended = fields.BooleanField(default=False)

    @property
    def deep_url(self):
        """Allows deleted files to resolve to a view
        that will provide a nice error message and http.GONE
        """
        return self.node.web_url_for('addon_deleted_file', trashed_id=self._id)

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'files'

    @property
    def root_target_page(self):
        """The comment page type associated with TrashedFileNodes."""
        return 'files'

    @property
    def is_deleted(self):
        return True

    def belongs_to_node(self, node_id):
        """Check whether the file is attached to the specified node."""
        return self.node._id == node_id

    def get_extra_log_params(self, comment):
        return {'file': {'name': self.name, 'url': comment.get_comment_page_url()}}

    def restore(self, recursive=True, parent=None):
        """Recreate a StoredFileNode from the data in this object
        Will re-point all guids and finally remove itself
        :raises KeyExistsException:
        """
        data = self.to_storage()
        data.pop('deleted_on')
        data.pop('deleted_by')
        if parent:
            data['parent'] = parent._id
        elif data['parent']:
            # parent is an AbstractForeignField, so it gets stored as tuple
            data['parent'] = data['parent'][0]
        restored = FileNode.resolve_class(self.provider, int(self.is_file))(**data)
        if not restored.parent:
            raise ValueError('No parent to restore to')
        restored.save()

        # repoint guid
        for guid in Guid.find(Q('referent', 'eq', self)):
            guid.referent = restored
            guid.save()

        if recursive:
            for child in TrashedFileNode.find(Q('parent', 'eq', self)):
                child.restore(recursive=recursive, parent=restored)

        TrashedFileNode.remove_one(self)
        return restored

    def get_guid(self, create=False):
        """Attempt to find a Guid that points to this object.
        One will be created if requested.
        :rtype: Guid
        """
        try:
            # Note sometimes multiple GUIDs can exist for
            # a single object. Just go with the first one
            return Guid.find(Q('referent', 'eq', self))[0]
        except IndexError:
            if not create:
                return None
        return Guid.generate(self)


@unique_on(['node', 'name', 'parent', 'is_file', 'provider', 'path'])
class StoredFileNode(StoredObject, Commentable):
    """The storage backend for FileNode objects.
    This class should generally not be used or created manually as FileNode
    contains all the helpers required.
    A FileNode wraps a StoredFileNode to provider usable abstraction layer
    """

    __indices__ = [{
        'unique': False,
        'key_or_list': [
            ('path', pymongo.ASCENDING),
            ('node', pymongo.ASCENDING),
            ('is_file', pymongo.ASCENDING),
            ('provider', pymongo.ASCENDING),
        ]
    }, {
        'unique': False,
        'key_or_list': [
            ('node', pymongo.ASCENDING),
            ('is_file', pymongo.ASCENDING),
            ('provider', pymongo.ASCENDING),
        ]
    }, {
        'unique': False,
        'key_or_list': [
            ('parent', pymongo.ASCENDING),
        ]
    }]

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    # The last time the touch method was called on this FileNode
    last_touched = fields.DateTimeField()
    # A list of dictionaries sorted by the 'modified' key
    # The raw output of the metadata request deduped by etag
    # Add regardless it can be pinned to a version or not
    history = fields.DictionaryField(list=True)
    # A concrete version of a FileNode, must have an identifier
    versions = fields.ForeignField('FileVersion', list=True)

    node = fields.ForeignField('Node', required=True)
    parent = fields.ForeignField('StoredFileNode', default=None)

    is_file = fields.BooleanField(default=True)
    provider = fields.StringField(required=True)

    name = fields.StringField(required=True)
    path = fields.StringField(required=True)
    materialized_path = fields.StringField(required=True)

    # The User that has this file "checked out"
    # Should only be used for OsfStorage
    checkout = fields.AbstractForeignField('User')

    #Tags for a file, currently only used for osfStorage
    tags = fields.ForeignField('Tag', list=True)

    # For Django compatibility
    @property
    def pk(self):
        return self._id

    # For Django compatibility
    # TODO Find a better way
    @property
    def node_id(self):
        return self.node._id

    @property
    def deep_url(self):
        return self.wrapped().deep_url

    @property
    def absolute_api_v2_url(self):
        path = '/files/{}/'.format(self._id)
        return util.api_v2_url(path)

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
    def is_deleted(self):
        if self.provider == 'osfstorage':
            return False

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
        return FileNode.resolve_class(self.provider, int(self.is_file))(self)

    def get_guid(self, create=False):
        """Attempt to find a Guid that points to this object.
        One will be created if requested.
        :rtype: Guid
        """
        try:
            # Note sometimes multiple GUIDs can exist for
            # a single object. Just go with the first one
            return Guid.find(Q('referent', 'eq', self))[0]
        except IndexError:
            if not create:
                return None
        return Guid.generate(self)


class FileNodeMeta(type):
    """Keeps track of subclasses of the ``FileNode`` object
    Inserts all into the PROVIDER_MAP following the pattern:
    {
        provider: [ProviderFolder, ProviderFile, ProviderFileNode]
    }
    """

    def __init__(cls, name, bases, dct):
        super(FileNodeMeta, cls).__init__(name, bases, dct)
        if hasattr(cls, 'provider'):
            cls_map = PROVIDER_MAP.setdefault(cls.provider, [None, None, None])
            index = int(getattr(cls, 'is_file', 2))

            if cls_map[index] is not None:
                raise ValueError('Conflicting providers')

            cls_map[index] = cls


class FileNode(object):
    """The base class for the entire files storage system.
    Use for querying on all files and folders in the database
    Note: This is a proxy object for StoredFileNode
    """
    FOLDER, FILE, ANY = 0, 1, 2

    __metaclass__ = FileNodeMeta

    @classmethod
    def create(cls, **kwargs):
        """A layer of abstraction around the creation of FileNodes.
        Provides hook in points for subclasses
        This is used only for GUID creation.
        """
        assert hasattr(cls, 'is_file') and hasattr(cls, 'provider'), 'Must have is_file and provider to call create'
        kwargs['is_file'] = cls.is_file
        kwargs['provider'] = cls.provider
        return cls(**kwargs)

    @classmethod
    def get_or_create(cls, node, path):
        """Tries to find a FileNode with node and path
        See FileNode.create
        Note: Osfstorage overrides this method due to odd database constraints
        """
        path = '/' + path.lstrip('/')
        try:
            # Note: Possible race condition here
            # Currently create then find is not super feasable as create would require a
            # call to save which we choose not to call to avoid filling  the database
            # with notfound/googlebot files/url. Raising 404 errors may roll back the transaction however
            return cls.find_one(Q('node', 'eq', node) & Q('path', 'eq', path))
        except NoResultsFound:
            return cls.create(node=node, path=path)

    @classmethod
    def get_file_guids(cls, materialized_path, provider, node, guids=None):
        guids = guids or []
        materialized_path = '/' + materialized_path.lstrip('/')
        if materialized_path.endswith('/'):
            folder_children = cls.find(Q('provider', 'eq', provider) &
                                       Q('node', 'eq', node) &
                                       Q('materialized_path', 'startswith', materialized_path))
            for item in folder_children:
                if item.kind == 'file':
                    guid = item.get_guid()
                    if guid:
                        guids.append(guid._id)
        else:
            try:
                file_obj = cls.find_one(Q('node', 'eq', node) & Q('materialized_path', 'eq', materialized_path))
            except NoResultsFound:
                return guids
            guid = file_obj.get_guid()
            if guid:
                guids.append(guid._id)

        return guids

    @classmethod
    def resolve_class(cls, provider, _type=2):
        """Resolve a provider and type to the appropriate subclass.
        Usage:
            >>> FileNode.resolve_class('box', FileNode.ANY)  # BoxFileNode
            >>> FileNode.resolve_class('dropbox', FileNode.FILE)  # DropboxFile
        :rtype: Subclass of FileNode
        """
        try:
            return PROVIDER_MAP[provider][int(_type)]
        except IndexError:
            raise exceptions.SubclassNotFound('_type must be 0, 1, or 2')
        except KeyError:
            raise exceptions.SubclassNotFound(provider)

    @classmethod
    def _filter(cls, qs=None):
        """Creates an odm query to limit the scope of whatever search method
        to the given class.
        :param qs RawQuery: An odm query or None
        :rtype: RawQuery or None
        """
        # Build a list of all possible contraints leaving None when appropriate
        # filter(None, ...) removes all falsey values
        qs = filter(None, (qs,
            Q('is_file', 'eq', cls.is_file) if hasattr(cls, 'is_file') else None,
            Q('provider', 'eq', cls.provider) if hasattr(cls, 'provider') else None,
        ))
        # If out list is empty return None; there's no filters to be applied
        if not qs:
            return None
        # Use reduce to & together all our queries. equavilent to:
        # return q1 & q2 ... & qn
        return functools.reduce(lambda q1, q2: q1 & q2, qs)

    @classmethod
    def find(cls, qs=None):
        """A proxy for StoredFileNode.find but applies class based contraints.
        Wraps The MongoQuerySet in a GenWrapper this overrides the __iter__ of
        MongoQuerySet to return wrapped objects
        :rtype: GenWrapper<MongoQuerySet<cls>>
        """
        return utils.GenWrapper(StoredFileNode.find(cls._filter(qs)))

    @classmethod
    def find_one(cls, qs):
        """A proxy for StoredFileNode.find_one but applies class based contraints.
        :rtype: cls
        """
        return StoredFileNode.find_one(cls._filter(qs)).wrapped()

    @classmethod
    def files_checked_out(cls, user):
        """
        :param user: The user with checkedout files
        :return: A queryset of all FileNodes checked out by user
        """
        return cls.find(Q('checkout', 'eq', user))

    @classmethod
    def load(cls, _id):
        """A proxy for StoredFileNode.load requires the wrapped version of the found value
        to be an instance of cls.
        :rtype: cls
        """
        inst = StoredFileNode.load(_id)
        if not inst:
            return None
        inst = inst.wrapped()
        assert isinstance(inst, cls), 'Loaded object {} is not of type {}'.format(inst, cls)
        return inst

    @property
    def parent(self):
        """A proxy to self.stored_object.parent but forces it to be wrapped.
        """
        if self.stored_object.parent:
            return self.stored_object.parent.wrapped()
        return None

    @parent.setter
    def parent(self, val):
        """A proxy to self.stored_object.parent but will unwrap it when need be
        """
        if isinstance(val, FileNode):
            val = val.stored_object
        self.stored_object.parent = val

    @property
    def deep_url(self):
        """The url that this filenodes guid should resolve to.
        Implemented here so that subclasses may override it or path.
        See OsfStorage or PathFollowingNode.
        """
        return self.node.web_url_for('addon_view_or_download_file', provider=self.provider, path=self.path.strip('/'))

    @property
    def kind(self):
        """Whether this FileNode is a file or folder as a string.
        Used for serialization and backwards compatability
        :rtype: str
        :returns: 'file' or 'folder'
        """
        return 'file' if self.is_file else 'folder'

    def __init__(self, *args, **kwargs):
        """Contructor for FileNode's subclasses
        If called with only a StoredFileNode it will be attached to self
        Otherwise:
        Injects provider and is_file when appropriate.
        Creates a new StoredFileNode with kwargs, not saved.
        Then attaches stored_object to self
        """
        if args and isinstance(args[0], StoredFileNode):
            assert len(args) == 1
            assert len(kwargs) == 0
            self.stored_object = args[0]
        else:
            if hasattr(self, 'provider'):
                kwargs['provider'] = self.provider
            if hasattr(self, 'is_file'):
                kwargs['is_file'] = self.is_file
            self.stored_object = StoredFileNode(*args, **kwargs)

    def save(self):
        """A proxy to self.stored_object.save.
        Implemented top level so that child class may override it
        and just call super.save rather than self.stored_object.save
        """
        return self.stored_object.save()

    def serialize(self, **kwargs):
        return {
            'id': self._id,
            'path': self.path,
            'name': self.name,
            'kind': self.kind,
        }

    def generate_waterbutler_url(self, **kwargs):
        return util.waterbutler_api_url_for(
            self.node._id,
            self.provider,
            self.path,
            **kwargs
        )

    def delete(self, user=None, parent=None):
        """Move self into the TrashedFileNode collection
        and remove it from StoredFileNode
        :param user User or None: The user that deleted this FileNode
        """
        trashed = self._create_trashed(user=user, parent=parent)
        self._repoint_guids(trashed)
        self.node.save()
        StoredFileNode.remove_one(self.stored_object)
        return trashed

    def copy_under(self, destination_parent, name=None):
        return utils.copy_files(self, destination_parent.node, destination_parent, name=name)

    def move_under(self, destination_parent, name=None):
        self.name = name or self.name
        self.parent = destination_parent.stored_object
        self._update_node(save=True)  # Trust _update_node to save us

        return self

    def update(self, revision, data, save=True, user=None):
        """Note: User is a kwargs here because of special requirements of
        dataverse and django
        See dataversefile.update
        """
        self.name = data['name']
        self.materialized_path = data['materialized']
        self.last_touched = datetime.datetime.utcnow()
        if save:
            self.save()

    def _create_trashed(self, save=True, user=None, parent=None):
        trashed = TrashedFileNode(
            _id=self._id,
            name=self.name,
            path=self.path,
            node=self.node,
            parent=parent or self.parent,
            history=self.history,
            is_file=self.is_file,
            checkout=self.checkout,
            provider=self.provider,
            versions=self.versions,
            last_touched=self.last_touched,
            materialized_path=self.materialized_path,

            deleted_by=user
        )
        if save:
            trashed.save()
        return trashed

    def _repoint_guids(self, updated):
        for guid in Guid.find(Q('referent', 'eq', self)):
            guid.referent = updated
            guid.save()

    def _update_node(self, recursive=True, save=True):
        if self.parent is not None:
            self.node = self.parent.node
        if save:
            self.save()
        if recursive and not self.is_file:
            for child in self.children:
                child._update_node(save=save)

    def __getattr__(self, name):
        """For the purpose of proxying all calls to the below stored_object
        Saves typing out ~10 properties or so
        """
        if 'stored_object' in self.__dict__:
            try:
                return getattr(self.stored_object, name)
            except AttributeError:
                pass  # Avoids error message about the underlying object
        return object.__getattribute__(self, name)

    def __setattr__(self, name, val):
        # Property setters are called after __setattr__ is called
        # If the requested attribute is a property with a setter go ahead and use it
        maybe_prop = getattr(self.__class__, name, None)
        if isinstance(maybe_prop, property) and maybe_prop.fset is not None:
            return object.__setattr__(self, name, val)
        if 'stored_object' in self.__dict__:
            return setattr(self.stored_object, name, val)
        return object.__setattr__(self, name, val)

    def __eq__(self, other):
        return self.stored_object == getattr(other, 'stored_object', None)

    def __repr__(self):
        return '<{}(name={!r}, node={!r})>'.format(
            self.__class__.__name__,
            self.stored_object.name,
            self.stored_object.node
        )


class File(FileNode):
    is_file = True
    version_identifier = 'revision'  # For backwards compatability

    def get_version(self, revision, required=False):
        """Find a version with identifier revision
        :returns: FileVersion or None
        :raises: VersionNotFoundError if required is True
        """
        for version in reversed(self.versions):
            if version.identifier == revision:
                break
        else:
            if required:
                raise exceptions.VersionNotFoundError(revision)
            return None
        return version

    def update_version_metadata(self, location, metadata):
        for version in reversed(self.versions):
            if version.location == location:
                version.update_metadata(metadata)
                return
        raise exceptions.VersionNotFoundError(location)

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
        # For backwards compatability
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
                default=datetime.datetime.utcnow()  # Just incase nothing can be parsed
            )

        # if revision is none then version is the latest version
        # Dont save the latest information
        if revision is not None:
            version.save()
            self.versions.append(version)

        for entry in self.history:
            if entry['etag'] == data['etag']:
                break
        else:
            # Insert into history if there is no matching etag
            utils.insort(self.history, data, lambda x: x['modified'])

        # Finally update last touched
        self.last_touched = datetime.datetime.utcnow()

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

    def serialize(self):
        if not self.versions:
            return dict(
                super(File, self).serialize(),
                size=None,
                version=None,
                modified=None,
                contentType=None,
                downloads=self.get_download_count(),
                checkout=self.checkout._id if self.checkout else None,
            )

        version = self.versions[-1]
        return dict(
            super(File, self).serialize(),
            size=version.size,
            downloads=self.get_download_count(),
            checkout=self.checkout._id if self.checkout else None,
            version=version.identifier if self.versions else None,
            contentType=version.content_type if self.versions else None,
            modified=version.date_modified.isoformat() if version.date_modified else None,
        )


class Folder(FileNode):
    is_file = False

    @property
    def children(self):
        """Finds all Filenodes that view self as a parent
        :returns: A GenWrapper for all children
        :rtype: GenWrapper<MongoQuerySet<cls>>
        """
        return FileNode.find(Q('parent', 'eq', self._id))

    def delete(self, recurse=True, user=None, parent=None):
        trashed = self._create_trashed(user=user, parent=parent)
        if recurse:
            for child in self.children:
                child.delete(user=user, parent=trashed)
        self._repoint_guids(trashed)
        StoredFileNode.remove_one(self.stored_object)
        return trashed

    def append_file(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, FileNode.FILE, path=path, materialized_path=materialized_path, save=save)

    def append_folder(self, name, path=None, materialized_path=None, save=True):
        return self._create_child(name, FileNode.FOLDER, path=path, materialized_path=materialized_path, save=save)

    def _create_child(self, name, kind, path=None, materialized_path=None, save=True):
        child = FileNode.resolve_class(self.provider, kind)(
            name=name,
            node=self.node,
            path=path or '/' + name,
            parent=self.stored_object,
            materialized_path=materialized_path or
            os.path.join(self.materialized_path, name) + '/' if not kind else ''
        ).wrapped()
        if save:
            child.save()
        return child

    def find_child_by_name(self, name, kind=2):
        return FileNode.resolve_class(self.provider, kind).find_one(
            Q('name', 'eq', name) &
            Q('parent', 'eq', self)
        )


class FileVersion(StoredObject):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    creator = fields.ForeignField('user')

    identifier = fields.StringField(required=True)

    # Date version record was created. This is the date displayed to the user.
    date_created = fields.DateTimeField(auto_now_add=True)

    # Dictionary specifying all information needed to locate file on backend
    # {
    #     'service': 'cloudfiles',  # required
    #     'container': 'osf',       # required
    #     'object': '20c53b',       # required
    #     'worker_url': '127.0.0.1',
    #     'worker_host': 'upload-service-1',
    # }
    location = fields.DictionaryField(default=None, validate=utils.validate_location)

    # Dictionary containing raw metadata from upload service response
    # {
    #     'size': 1024,                            # required
    #     'content_type': 'text/plain',            # required
    #     'date_modified': '2014-11-07T20:24:15',  # required
    #     'md5': 'd077f2',
    # }
    metadata = fields.DictionaryField()

    size = fields.IntegerField()
    content_type = fields.StringField()
    # Date file modified on third-party backend. Not displayed to user, since
    # this date may be earlier than the date of upload if the file already
    # exists on the backend
    date_modified = fields.DateTimeField()

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
            # TODO handle the timezone here the user that updates the file may see an
            # Incorrect version
            self.date_modified = parse_date(self.metadata['modified'], ignoretz=True)

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
