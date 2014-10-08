# -*- coding: utf-8 -*-

import os
import bson

from modularodm import fields, Q
from modularodm import exceptions as modm_errors

from framework.mongo import StoredObject

from website.addons.base import AddonNodeSettingsBase, GuidFile

from website.addons.osfstorage import errors


oid_primary_key = fields.StringField(
    primary=True,
    default=lambda: str(bson.ObjectId())
)


def copy_file_tree_stable(tree, node_settings):
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
    versions = [
        version for version in record.versions
        if version.status == status['COMPLETE']
    ]
    if versions:
        clone = record.clone()
        clone.versions = versions
        clone.node_settings = node_settings
        clone.save()
        return clone
    return None


def copy_files_stable(files, node_settings):
    if isinstance(files, FileTree):
        return copy_file_tree_stable(files, node_settings)
    if isinstance(files, FileRecord):
        return copy_file_record_stable(files, node_settings)
    raise TypeError('Input must be `FileTree` or `FileRecord`')


class OsfStorageNodeSettings(AddonNodeSettingsBase):

    file_tree = fields.ForeignField('FileTree')

    def after_fork(self, node, fork, user, save=True):
        """
        """
        clone, message = super(OsfStorageNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )
        # Must save clone to attach to `FileTree` and `FileRecord` objects
        clone.save()
        clone.tree = copy_file_tree_stable(self.file_tree, clone)
        return clone, message

    def after_register(self, node, registration, user, save=True):
        """
        """
        clone, message = super(OsfStorageNodeSettings, self).after_register(
            node=node, registration=registration, user=user, save=False
        )
        # Must save clone to attach to `FileTree` and `FileRecord` objects
        clone.save()
        clone.tree = copy_file_tree_stable(self.file_tree, clone)
        return clone, message


def get_parent_class(klass):
    return FileTree


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

    @classmethod
    def find_by_path(cls, path, node_settings):
        try:
            return cls.find_one(
                Q('path', 'eq', path) &
                Q('node_settings', 'eq', node_settings._id)
            )
        except (modm_errors.NoResultsFound, modm_errors.MultipleResultsFound):
            return None

    @classmethod
    def get_or_create(cls, path, node_settings):
        obj = cls.find_by_path(path, node_settings)
        if obj:
            return obj
        obj = cls(path=path, node_settings=node_settings)
        obj.save()
        if path:
            parent_path, _ = os.path.split(path)
            parent_class = get_parent_class(cls)
            parent_obj = parent_class.get_or_create(
                parent_path,
                node_settings,
            )
            parent_obj.children.append(obj)
            parent_obj.save()
        else:
            assert node_settings.file_tree is None
            node_settings.file_tree = obj
            node_settings.save()
        return obj

    def __repr__(self):
        return '<{}(path={!r}, node_settings={!r})>'.format(
            self.__class__.__name__,
            self.path,
            self.node_settings._id,
        )


class FileTree(BaseFileObject):

    _id = oid_primary_key
    children = fields.AbstractForeignField(list=True)


class FileRecord(BaseFileObject):

    _id = oid_primary_key
    is_deleted = fields.BooleanField(default=False)
    versions = fields.ForeignField('FileVersion', list=True)

    def get_latest_version(self, required=False):
        try:
            return self.versions[-1]
        except IndexError:
            if required:
                raise errors.NoVersionsError
            return None

    def create_pending_version(self, signature):
        latest_version = self.get_latest_version()
        if latest_version and latest_version.pending:
            raise errors.PathLockedError
        if latest_version and latest_version.signature == signature:
            raise errors.SignatureConsumedError
        version = FileVersion(
            status=status['PENDING'],
            signature=signature,
        )
        version.save()
        self.versions.append(version)
        self.save()
        return version

    def resolve_pending_version(self, signature, location, metadata):
        latest_version = self.get_latest_version(required=True)
        latest_version.resolve(signature, location, metadata)
        return latest_version

    def cancel_pending_version(self, signature):
        latest_version = self.get_latest_version(required=True)
        latest_version.cancel(signature)
        return latest_version

    def delete(self):
        if self.is_deleted:
            raise errors.DeleteError
        self.is_deleted = True

    def undelete(self):
        if not self.is_deleted:
            raise errors.UndeleteError
        self.is_deleted = False


status = {
    'PENDING': 'pending',
    'COMPLETE': 'complete',
    'FAILED': 'failed',
}
def validate_status(value):
    if value not in status.values():
        raise modm_errors.ValidationValueError


class FileVersion(StoredObject):

    _id = oid_primary_key

    status = fields.StringField(validate=validate_status)
    location = fields.DictionaryField()
    signature = fields.StringField()

    size = fields.IntegerField()
    content_type = fields.StringField()
    date_modified = fields.DateTimeField()

    @property
    def pending(self):
        return self.status == status['PENDING']

    @property
    def location_hash(self):
        if self.location is None:
            return None
        return self.location['object']

    def before_update(self, signature):
        if not self.pending:
            raise errors.VersionNotPendingError
        if self.signature != signature:
            raise errors.PendingSignatureMismatchError

    def resolve(self, signature, location, metadata):
        self.before_update(signature)
        self.status = status['COMPLETE']
        self.location = location
        for key, value in metadata.iteritems():
            setattr(self, key, value)
        self.save()

    def cancel(self, signature):
        self.before_update(signature)
        self.status = status['FAILED']
        self.save()


LOCATION_KEYS = ['service', 'container', 'object']
@FileVersion.subscribe('before_save')
def validate_file_version(schema, instance):
    if instance.status == status['COMPLETE']:
        if any(key not in instance.location for key in LOCATION_KEYS):
            raise modm_errors.ValidationValueError


class StorageFile(GuidFile):

    path = fields.StringField(required=True, index=True)

    @property
    def file_url(self):
        return os.path.join('osfstorage', 'files', self.path)

    def get_download_path(self, version_idx):
        return '/{0}/download/?version={1}'.format(self._id, version_idx)

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

