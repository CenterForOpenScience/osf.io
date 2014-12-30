# encoding: utf-8

import os
import bson
import logging

import furl

from modularodm import fields, Q
from modularodm import exceptions as modm_errors

from framework.auth import Auth
from framework.mongo import StoredObject
from framework.analytics import get_basic_counters

from website.models import NodeLog
from website.addons.base import AddonNodeSettingsBase, GuidFile

from website.addons.osfstorage import logs
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings


logger = logging.getLogger(__name__)

oid_primary_key = fields.StringField(
    primary=True,
    default=lambda: str(bson.ObjectId())
)


def copy_file_tree_stable(tree, node_settings):
    """Copy file tree, recursively creating stable copies of its children.

    :param OsfStorageFileTree tree: Tree to copy
    :param node_settings: Root node settings record
    """
    children = filter(
        lambda item: item is not None,
        map(
            lambda child: copy_files_stable(child, node_settings),
            tree.children
        )
    )
    clone = tree.clone()
    clone.children = children
    clone.node_settings = node_settings
    clone.save()
    return clone


def copy_file_record_stable(record, node_settings):
    """Copy stable versions of an `OsfStorageFileRecord`. Versions are copied
    by primary key and will not be duplicated in the database.

    :param OsfStorageFileRecord record: Record to copy
    :param node_settings: Root node settings record
    :return: Cloned `OsfStorageFileRecord` if any stable versions were found,
        else ``None``
    """
    versions = [
        version for version in record.versions
        if not version.pending
    ]
    if versions:
        clone = record.clone()
        clone.versions = versions
        clone.node_settings = node_settings
        clone.save()
        return clone
    return None


def copy_files_stable(files, node_settings):
    if isinstance(files, OsfStorageFileTree):
        return copy_file_tree_stable(files, node_settings)
    if isinstance(files, OsfStorageFileRecord):
        return copy_file_record_stable(files, node_settings)
    raise TypeError('Input must be `OsfStorageFileTree` or `OsfStorageFileRecord`')


class OsfStorageNodeSettings(AddonNodeSettingsBase):

    file_tree = fields.ForeignField('OsfStorageFileTree')

    def copy_contents_to(self, dest):
        """Copy file tree and contents to destination. Note: destination must be
        saved before copying so that copied items can refer to it.

        :param OsfStorageNodeSettings dest: Destination settings object
        """
        dest.save()
        if self.file_tree:
            dest.file_tree = copy_file_tree_stable(self.file_tree, dest)
            dest.save()

    def after_fork(self, node, fork, user, save=True):
        clone, message = super(OsfStorageNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )
        self.copy_contents_to(clone)
        return clone, message

    def after_register(self, node, registration, user, save=True):
        clone, message = super(OsfStorageNodeSettings, self).after_register(
            node=node, registration=registration, user=user, save=False
        )
        self.copy_contents_to(clone)
        return clone, message

    def serialize_waterbutler_settings(self):
        ret = {
            'callback': self.owner.api_url_for(
                'osf_storage_crud_hook_get',
                _absolute=True,
            ),
            'metadata': self.owner.api_url_for(
                'osf_storage_hgrid_contents',
                _absolute=True,
            ),
        }
        ret.update(settings.WATERBUTLER_SETTINGS)
        return ret

    def serialize_waterbutler_credentials(self):
        return settings.WATERBUTLER_CREDENTIALS

    def create_waterbutler_log(self, auth, action, metadata):
        # pass
        self.owner.add_log(
            'osf_storage_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'urls': logs.build_log_urls(self.owner, metadata['path'])
            }
        )


class BaseFileObject(StoredObject):

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
    def parent(self):
        parents = getattr(self, '_parent', None)
        if parents:
            assert len(parents) == 1
            return parents[0]
        return None

    @property
    def node(self):
        return self.node_settings.owner

    @classmethod
    def parent_class(cls):
        raise NotImplementedError

    @classmethod
    def find_by_path(cls, path, node_settings, touch=True):
        """Find a record by path and root settings record.

        :param str path: Path to file or directory
        :param node_settings: Root node settings record
        :param bool touch: Handle expired records
        """
        try:
            obj = cls.find_one(
                Q('path', 'eq', path) &
                Q('node_settings', 'eq', node_settings._id)
            )
            if touch:
                obj.touch()
            return obj
        except (modm_errors.NoResultsFound, modm_errors.MultipleResultsFound):
            return None

    @classmethod
    def get_or_create(cls, path, node_settings, touch=True):
        """Get or create a record by path and root settings record.

        :param str path: Path to file or directory
        :param node_settings: Root node settings record
        :param bool touch: Handle expired records
        """
        obj = cls.find_by_path(path, node_settings, touch=touch)

        if obj:
            return obj, False

        obj = cls(path=path, node_settings=node_settings)
        obj.save()
        # Ensure all intermediate paths
        if path:
            parent_path, _ = os.path.split(path)
            parent_class = cls.parent_class()
            parent_obj, _ = parent_class.get_or_create(parent_path, node_settings)
            parent_obj.children.append(obj)
            parent_obj.save()
        else:
            assert node_settings.file_tree is None
            node_settings.file_tree = obj
            node_settings.save()

        return obj, True

    def touch(self):
        """Check whether the current object is valid. By default, always return
        `True`.
        """
        return True

    def get_download_count(self, version=None):
        """Return download count or `None` if this is not a file object (e.g. a
        folder).
        """
        return None

    def __repr__(self):
        return '<{}(path={!r}, node_settings={!r})>'.format(
            self.__class__.__name__,
            self.path,
            self.node_settings._id,
        )


class OsfStorageFileTree(BaseFileObject):

    _id = oid_primary_key
    children = fields.AbstractForeignField(list=True, backref='_parent')

    @classmethod
    def parent_class(cls):
        return OsfStorageFileTree


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

    def get_versions(self, page, size=settings.REVISIONS_PAGE_SIZE):
        start = len(self.versions) - (page * size)
        stop = max(0, start - size)
        indices = range(start, stop, -1)
        versions = [self.versions[idx - 1] for idx in indices]
        more = stop > 0
        return indices, versions, more

    def create_version(self, creator, location, metadata=None):
        version = OsfStorageFileVersion(creator=creator, location=location)
        latest_version = self.get_version()
        if latest_version and latest_version.is_duplicate(version):
            return latest_version
        version.save()
        if metadata:
            version.update_metadata(metadata)
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

    def remove_version(self, version):
        if len(self.versions) == 1:
            OsfStorageFileRecord.remove_one(self)
            retained_self = False
        else:
            self.versions.remove(version)
            self.save()
            retained_self = True
        OsfStorageFileVersion.remove_one(version)
        return retained_self

    def log(self, auth, action, version=True):
        node_logger = logs.OsfStorageNodeLogger(
            auth=auth,
            node=self.node,
            path=self.path,
        )
        extra = {'version': len(self.versions)} if version else None
        node_logger.log(action, extra=extra, save=True)

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
            self.log(auth, NodeLog.FILE_RESTORED)

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


identity = lambda value: value
metadata_fields = {
    # TODO: Add missing fields to WaterButler metadata
    # 'size': identity,
    # 'content_type': identity,
    # 'date_modified': parse_date,
}


class OsfStorageFileVersion(StoredObject):

    _id = oid_primary_key
    creator = fields.ForeignField('user', required=True)

    date_created = fields.DateTimeField(auto_now_add=True)

    # Dictionary specifying all information needed to locate file on backend
    # {
    #     'service': 'buttfiles',  # required
    #     'container': 'osf',       # required
    #     'object': '20c53b',       # required
    #     'worker_url': '127.0.0.1',
    #     'worker_host': 'upload-service-1',
    # }
    location = fields.DictionaryField()

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
    date_modified = fields.DateTimeField()

    @property
    def location_hash(self):
        # TODO: Throw error if object not present
        return self.location['object'] if self.location else None

    def is_duplicate(self, other):
        return (
            bool(self.location_hash) and
            self.location_hash == other.location_hash
        )

    def update_metadata(self, metadata):
        self.metadata.update(metadata)
        for key, parser in metadata_fields.iteritems():
            try:
                value = metadata[key]
            except KeyError:
                raise errors.MissingFieldError
            setattr(self, key, parser(value))
        self.save()


LOCATION_KEYS = ['service', settings.WATERBUTLER_RESOURCE, 'object']
@OsfStorageFileVersion.subscribe('before_save')
def validate_version_location(schema, instance):
    for key in LOCATION_KEYS:
        if key not in instance.location:
            raise modm_errors.ValidationValueError


# @OsfStorageFileVersion.subscribe('before_save')
# def validate_version_dates(schema, instance):
#     if not instance.date_resolved:
#         raise modm_errors.ValidationValueError
#     if instance.date_created > instance.date_resolved:
#         raise modm_errors.ValidationValueError


class OsfStorageGuidFile(GuidFile):

    path = fields.StringField(required=True, index=True)

    @property
    def file_url(self):
        return os.path.join('osfstorage', 'files', self.path)

    def get_download_path(self, version_idx):
        url = furl.furl('/{0}/'.format(self._id))
        url.args.update({
            'action': 'download',
            'version': version_idx,
            'mode': 'render',
        })
        return url.url

    @classmethod
    def get_or_create(cls, node, path):
        try:
            obj = cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            )
        except modm_errors.ModularOdmException:
            obj = cls(node=node, path=path)
            obj.save()
        return obj
