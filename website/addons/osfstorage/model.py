from __future__ import unicode_literals

import os
import bson
import logging

import furl

from modularodm import fields, Q
from dateutil.parser import parse as parse_date
from modularodm.exceptions import NoResultsFound
from modularodm.storage.base import KeyExistsException

from framework.auth import Auth
from framework.mongo import StoredObject
from framework.mongo.utils import unique_on
from framework.analytics import get_basic_counters

from website.models import NodeLog
from website.addons.base import AddonNodeSettingsBase, GuidFile

from website.addons.osfstorage import logs
from website.addons.osfstorage import utils
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings


logger = logging.getLogger(__name__)


class OsfStorageNodeSettings(AddonNodeSettingsBase):
    complete = True
    has_auth = True

    root_node = fields.ForeignField('OsfStorageFileNode')
    file_tree = fields.ForeignField('OsfStorageFileTree')

    # Temporary field to mark that a record has been migrated by the
    # migrate_from_oldels scripts
    _migrated_from_old_models = fields.BooleanField(default=False)

    def on_add(self):
        if self.root_node:
            return

        # A save is required here to both create and attach the root_node
        # When on_add is called the model that self refers to does not yet exist
        # in the database and thus odm cannot attach foreign fields to it
        self.save()
        # Note: The "root" node will always be "named" empty string
        root = OsfStorageFileNode(name='', kind='folder', node_settings=self)
        root.save()
        self.root_node = root
        self.save()

    def find_or_create_file_guid(self, path):
        return OsfStorageGuidFile.get_or_create(self.owner, path)

    def after_fork(self, node, fork, user, save=True):
        clone, message = super(OsfStorageNodeSettings, self).after_fork(
            node=node, fork=fork, user=user, save=False
        )
        clone.save()
        clone.root_node = utils.copy_files(self.root_node, clone)
        clone.save()

        return clone, message

    def after_register(self, node, registration, user, save=True):
        clone = self.clone()
        clone.owner = registration
        clone.save()

        clone.root_node = utils.copy_files(self.root_node, clone)
        clone.save()

        return clone, None

    def serialize_waterbutler_settings(self):
        ret = {
            'rootId': self.root_node._id,
            'copy': self.owner.api_url_for(
                'osf_storage_copy_hook',
                _absolute=True,
                _offload=True
            ),
            'move': self.owner.api_url_for(
                'osf_storage_move_hook',
                _absolute=True,
                _offload=True
            ),
            'callback': self.owner.api_url_for(
                'osf_storage_update_metadata_hook',
                _absolute=True,
                _offload=True
            ),
            'metadata': self.owner.api_url_for(
                'osf_storage_get_metadata_hook',
                _absolute=True,
                _offload=True
            ),
            'revisions': self.owner.api_url_for(
                'osf_storage_get_revisions',
                _absolute=True,
                _offload=True
            ),
            'lineage': self.owner.api_url_for(
                'osf_storage_get_lineage',
                _absolute=True,
                _offload=True
            ),
            'createFolder': self.owner.api_url_for(
                'osf_storage_create_folder',
                _absolute=True,
            ),
        }
        ret.update(settings.WATERBUTLER_SETTINGS)
        return ret

    def serialize_waterbutler_credentials(self):
        return settings.WATERBUTLER_CREDENTIALS

    def create_waterbutler_log(self, auth, action, metadata):
        pass


@unique_on(['name', 'kind', 'parent', 'node_settings'])
class OsfStorageFileNode(StoredObject):
    """A node in the file tree of a given project
    Contains  references to a fileversion and stores information about
    deletion status and position in the tree

               root
              / | \
        child1  |  child3
                child2
                /
            grandchild1
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))

    is_deleted = fields.BooleanField(default=False)
    name = fields.StringField(required=True, index=True)
    kind = fields.StringField(required=True, index=True)
    parent = fields.ForeignField('OsfStorageFileNode', index=True)
    versions = fields.ForeignField('OsfStorageFileVersion', list=True)
    node_settings = fields.ForeignField('OsfStorageNodeSettings', required=True, index=True)

    @classmethod
    def create_child_by_path(cls, path, node_settings):
        """Attempts to create a child node from a path formatted as
        /parentid/child_name
        returns created, child_node
        """
        try:
            parent_id, child_name = path.strip('/').split('/')
            parent = cls.get_folder(parent_id, node_settings)
        except ValueError:
            try:
                parent, (child_name, ) = node_settings.root_node, path.strip('/').split('/')
            except ValueError:
                raise errors.InvalidPathError('Path {} is invalid'.format(path))

        try:
            if path.endswith('/'):
                return True, parent.append_folder(child_name)
            else:
                return True, parent.append_file(child_name)
        except KeyExistsException:
            if path.endswith('/'):
                return False, parent.find_child_by_name(child_name, kind='folder')
            else:
                return False, parent.find_child_by_name(child_name, kind='file')

    @classmethod
    def get(cls, path, node_settings):
        path = path.strip('/')

        if not path:
            return node_settings.root_node

        return cls.find_one(
            Q('_id', 'eq', path) &
            Q('node_settings', 'eq', node_settings)
        )

    @classmethod
    def get_folder(cls, path, node_settings):
        path = path.strip('/')

        if not path:
            return node_settings.root_node

        return cls.find_one(
            Q('_id', 'eq', path) &
            Q('kind', 'eq', 'folder') &
            Q('node_settings', 'eq', node_settings)
        )

    @classmethod
    def get_file(cls, path, node_settings):
        return cls.find_one(
            Q('_id', 'eq', path.strip('/')) &
            Q('kind', 'eq', 'file') &
            Q('node_settings', 'eq', node_settings)
        )

    @property
    @utils.must_be('folder')
    def children(self):
        return self.__class__.find(Q('parent', 'eq', self._id))

    @property
    def is_folder(self):
        return self.kind == 'folder'

    @property
    def is_file(self):
        return self.kind == 'file'

    @property
    def path(self):
        return '/{}{}'.format(self._id, '/' if self.is_folder else '')

    @property
    def node(self):
        return self.node_settings.owner

    def materialized_path(self):
        """creates the full path to a the given filenode
        Note: Possibly high complexity/ many database calls
        USE SPARINGLY
        """
        # Note: ODM cache can be abused here
        # for highly nested folders calling
        # list(self.__class__.find(Q(nodesetting),Q(folder))
        # may result in a massive increase in performance
        def lineage():
            current = self
            while current:
                yield current
                current = current.parent

        path = os.path.join(*reversed([x.name for x in lineage()]))
        if self.is_folder:
            return '/{}/'.format(path)
        return '/{}'.format(path)

    @utils.must_be('folder')
    def find_child_by_name(self, name, kind='file'):
        return self.__class__.find_one(
            Q('name', 'eq', name) &
            Q('kind', 'eq', kind) &
            Q('parent', 'eq', self)
        )

    def append_folder(self, name, save=True):
        return self._create_child(name, 'folder', save=save)

    def append_file(self, name, save=True):
        return self._create_child(name, 'file', save=save)

    @utils.must_be('folder')
    def _create_child(self, name, kind, save=True):
        child = OsfStorageFileNode(
            name=name,
            kind=kind,
            parent=self,
            node_settings=self.node_settings
        )
        if save:
            child.save()
        return child

    def get_download_count(self, version=None):
        if self.is_folder:
            return None

        parts = ['download', self.node._id, self._id]
        if version is not None:
            parts.append(version)
        page = ':'.join([format(part) for part in parts])
        _, count = get_basic_counters(page)

        return count or 0

    @utils.must_be('file')
    def get_version(self, index=-1, required=False):
        try:
            return self.versions[index]
        except IndexError:
            if required:
                raise errors.VersionNotFoundError
            return None

    @utils.must_be('file')
    def create_version(self, creator, location, metadata=None, log=True):
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

        if log:
            self.log(
                Auth(creator),
                NodeLog.FILE_UPDATED if len(self.versions) > 1 else NodeLog.FILE_ADDED,
            )

        return version

    @utils.must_be('file')
    def update_version_metadata(self, location, metadata):
        for version in reversed(self.versions):
            if version.location == location:
                version.update_metadata(metadata)
                return
        raise errors.VersionNotFoundError

    def log(self, auth, action, version=True):
        node_logger = logs.OsfStorageNodeLogger(
            auth=auth,
            node=self.node,
            path=self.path,
            full_path=self.materialized_path(),
        )
        extra = {'version': len(self.versions)} if version else None
        node_logger.log(action, extra=extra, save=True)

    def delete(self, auth, recurse=True, log=True):
        if self.is_deleted:
            raise errors.DeleteError

        self.is_deleted = True
        self.save()

        if recurse and self.is_folder:
            for child in self.children:
                try:
                    child.delete(auth, recurse=recurse, log=log)
                except errors.DeleteError:
                    pass  # If a child is already deleted ignore the error

        if log:
            self.log(auth, NodeLog.FILE_REMOVED, version=False)

    def undelete(self, auth, recurse=True, log=True):
        if not self.is_deleted:
            raise errors.UndeleteError

        self.is_deleted = False
        self.save()

        if recurse and self.is_folder:
            for child in self.children:
                child.undelete(auth, recurse=recurse, log=log)

        if log:
            self.log(auth, NodeLog.FILE_ADDED if self.is_file else NodeLog.FOLDER_CREATED)

    def serialized(self, include_full=False):
        """Build Treebeard JSON for folder or file.
        """
        data = {
            'path': self.path,
            'name': self.name,
            'kind': self.kind,
            'version': len(self.versions),
            'downloads': self.get_download_count(),
        }
        if include_full:
            data['fullPath'] = self.materialized_path()
        return data

    def copy_to_path(self, path, dest_node_addon=None, auth=None, log=True):
        try:
            dest_path, new_name = path.strip('/').split('/')
        except ValueError:
            dest_path, new_name = path, self.name

        if not dest_path.strip('/'):
            dest_node = self.node_settings.root_node
        else:
            dest_node = self.__class__.get(dest_path, dest_node_addon or self.node_settings)

        # try:
        #     new_node = dest_node.find_child_by_name(new_name, kind=self.kind)
        #     new_node.versions = self.versions
        # except NoResultsFound:
        new_node = self.clone()

        new_node.name = new_name
        new_node.parent = dest_node

        new_node.save()

        return True, new_node

    def move_to_path(self, path, dest_node_addon=None, auth=None, log=True):
        try:
            dest_path, new_name = path.strip('/').split('/')
        except ValueError:
            dest_path, new_name = path, self.name

        if not dest_path.strip('/'):
            dest_node = self.node_settings.root_node
        else:
            dest_node = self.__class__.get(dest_path, dest_node_addon or self.node_settings)

        self.name = new_name
        self.parent = dest_node
        self.save()
        return False, self

    def __repr__(self):
        return '<{}(name={!r}, node_settings={!r})>'.format(
            self.__class__.__name__,
            self.name,
            self.to_storage()['node_settings']
        )


class OsfStorageFileVersion(StoredObject):
    """A version of an OsfStorageFileNode. contains information
    about where the file is located, hashes and datetimes
    """

    _id = fields.StringField(primary=True, default=lambda: str(bson.ObjectId()))
    creator = fields.ForeignField('user', required=True)

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
    location = fields.DictionaryField(validate=utils.validate_location)

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

    def is_duplicate(self, other):
        return self.location_hash == other.location_hash

    def update_metadata(self, metadata):
        self.metadata.update(metadata)
        self.content_type = self.metadata.get('contentType', None)
        try:
            self.size = self.metadata['size']
            self.date_modified = parse_date(self.metadata['modified'], ignoretz=True)
        except KeyError as err:
            raise errors.MissingFieldError(str(err))
        self.save()


@unique_on(['node', 'path', '_path', 'premigration_path'])
class OsfStorageGuidFile(GuidFile):
    """A reference back to a OsfStorageFileNode

    path is the "waterbutler path" as well as the path
    used to look up a filenode

    GuidFile.path == FileNode.path == '/' + FileNode._id
    """

    path = fields.StringField(required=True, index=True)
    provider = 'osfstorage'
    version_identifier = 'version'

    _path = fields.StringField(index=True)
    premigration_path = fields.StringField(index=True)
    path = fields.StringField(required=True, index=True)

    # Marker for invalid GUIDs that are associated with a node but not
    # part of a GUID's file tree, e.g. those generated by spiders
    _has_no_file_tree = fields.BooleanField(default=False)

    @classmethod
    def get_or_create(cls, node, path):
        try:
            return cls.find_one(
                Q('node', 'eq', node) &
                Q('path', 'eq', path)
            ), False
        except NoResultsFound:
            # Create new
            new = cls(node=node, path=path)
            new.save()
        return new, True

    @property
    def waterbutler_path(self):
        return self.path

    @property
    def unique_identifier(self):
        return self._metadata_cache['extra']['version']

    @property
    def file_url(self):
        return os.path.join('osfstorage', 'files', self.path.lstrip('/'))

    def get_download_path(self, version_idx):
        url = furl.furl('/{0}/'.format(self._id))
        url.args.update({
            'action': 'download',
            'version': version_idx,
            'mode': 'render',
        })
        return url.url

    @property
    def extra(self):
        if not self._metadata_cache:
            return {}

        return {
            'fullPath': self._metadata_cache['fullPath'],
        }
