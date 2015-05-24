# encoding: utf-8

import os
import bson
import logging

import pymongo

from modularodm import fields, Q
from modularodm import exceptions as modm_errors
from modularodm.storage.base import KeyExistsException

from framework.auth import Auth
from framework.mongo import StoredObject
from framework.analytics import get_basic_counters
from website.models import NodeLog

from website.addons.osfstorage import errors
from website.addons.osfstorage.model import OsfStorageFileVersion


logger = logging.getLogger(__name__)

oid_primary_key = fields.StringField(
    primary=True,
    default=lambda: str(bson.ObjectId())
)


class BaseFileObject(StoredObject):
    __indices__ = [
        {
            'key_or_list': [
                ('path', pymongo.ASCENDING),
                ('node_settings', pymongo.ASCENDING),
            ],
            'unique': True,
        }
    ]

    path = fields.StringField(required=True, index=True)
    node_settings = fields.ForeignField(
        'OsfStorageNodeSettings',
        required=True,
        index=True,
    )

    _meta = {
        'abstract': True,
    }

    @property
    def name(self):
        _, value = os.path.split(self.path)
        return value

    @property
    def extension(self):
        _, value = os.path.splitext(self.path)
        return value

    @property
    def node(self):
        return self.node_settings.owner

    @classmethod
    def parent_class(cls):
        raise NotImplementedError

    @classmethod
    def find_by_path(cls, path, node_settings):
        """Find a record by path and root settings record.

        :param str path: Path to file or directory
        :param node_settings: Root node settings record
        """
        try:
            obj = cls.find_one(
                Q('path', 'eq', path.rstrip('/')) &
                Q('node_settings', 'eq', node_settings._id)
            )
            return obj
        except modm_errors.NoResultsFound:
            return None

    @classmethod
    def get_or_create(cls, path, node_settings):
        """Get or create a record by path and root settings record.

        :param str path: Path to file or directory
        :param node_settings: Root node settings record
        :returns: Tuple of (record, created)
        """
        path = path.rstrip('/')

        try:
            obj = cls(path=path, node_settings=node_settings)
            obj.save()
        except KeyExistsException:
            obj = cls.find_by_path(path, node_settings)
            assert obj is not None
            return obj, False

        # Ensure all intermediate paths
        if path:
            parent_path, _ = os.path.split(path)
            parent_class = cls.parent_class()
            parent_obj, _ = parent_class.get_or_create(parent_path, node_settings)
            parent_obj.append_child(obj)
        else:
            node_settings.file_tree = obj
            node_settings.save()

        return obj, True

    def get_download_count(self, version=None):
        """Return download count or `None` if this is not a file object (e.g. a
        folder).
        """
        return None

    def __repr__(self):
        return '<{}(path={!r}, node_settings={!r})>'.format(
            self.__class__.__name__,
            self.path,
            self.to_storage()['node_settings']
        )


class OsfStorageFileTree(BaseFileObject):

    _id = oid_primary_key
    children = fields.AbstractForeignField(list=True)

    @classmethod
    def parent_class(cls):
        return OsfStorageFileTree

    def append_child(self, child):
        """Appending children through ODM introduces a race condition such that
        concurrent requests can overwrite previously added items; use the native
        `addToSet` operation instead.
        """
        collection = self._storage[0].store
        collection.update(
            {'_id': self._id},
            {'$addToSet': {'children': (child._id, child._name)}}
        )
        # Updating MongoDB directly means the cache is wrong; reload manually
        self.reload()

    @property
    def is_deleted(self):
        return False


class OsfStorageFileRecord(BaseFileObject):

    _id = oid_primary_key
    is_deleted = fields.BooleanField(default=False)
    versions = fields.ForeignField('OsfStorageFileVersion', list=True)

    @classmethod
    def parent_class(cls):
        return OsfStorageFileTree

    def get_version(self, index=-1, required=False):
        try:
            return self.versions[index]
        except IndexError:
            if required:
                raise errors.VersionNotFoundError
            return None

    def get_versions(self, page, size):
        start = len(self.versions) - (page * size)
        stop = max(0, start - size)
        indices = range(start, stop, -1)
        versions = [self.versions[idx - 1] for idx in indices]
        more = stop > 0
        return indices, versions, more

    def create_version(self, creator, location, metadata=None):
        latest_version = self.get_version()
        version = OsfStorageFileVersion(creator=creator, location=location)

        if latest_version and latest_version.is_duplicate(version):
            if self.is_deleted:
                self.undelete(Auth(creator))
            return latest_version

        if metadata:
            version.update_metadata(metadata)

        version.save()
        self.versions.append(version)
        self.is_deleted = False
        self.save()
        self.log(
            Auth(creator),
            NodeLog.FILE_UPDATED if len(self.versions) > 1 else NodeLog.FILE_ADDED,
        )
        return version

    def update_version_metadata(self, location, metadata):
        for version in reversed(self.versions):
            if version.location == location:
                version.update_metadata(metadata)
                return
        raise errors.VersionNotFoundError

    def delete(self, auth, log=True):
        if self.is_deleted:
            raise errors.DeleteError
        self.is_deleted = True
        self.save()
        if log:
            self.log(auth, NodeLog.FILE_REMOVED, version=False)

    def undelete(self, auth, log=True):
        if not self.is_deleted:
            raise errors.UndeleteError
        self.is_deleted = False
        self.save()
        if log:
            self.log(auth, NodeLog.FILE_ADDED)

    def get_download_count(self, version=None):
        """
        :param int version: Optional one-based version index
        """
        parts = ['download', self.node._id, self.path]
        if version is not None:
            parts.append(version)
        page = ':'.join([format(part) for part in parts])
        _, count = get_basic_counters(page)
        return count or 0
