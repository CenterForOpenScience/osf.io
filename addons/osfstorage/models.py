from __future__ import unicode_literals

import logging

from django.apps import apps
from django.db import models, connection
from django.contrib.contenttypes.models import ContentType
from psycopg2._psycopg import AsIs

from addons.base.models import BaseNodeSettings, BaseStorageAddon, BaseUserSettings
from osf.utils.fields import EncryptedJSONField
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.exceptions import InvalidTagError, NodeStateError, TagNotFoundError
from framework.auth.core import Auth
from osf.models.mixins import Loggable
from osf.models import AbstractNode
from osf.models.files import File, FileVersion, Folder, TrashedFileNode, BaseFileNode, BaseFileNodeManager
from osf.utils import permissions
from website.files import exceptions
from website.files import utils as files_utils
from website.util import api_url_for
from website import settings as website_settings
from addons.osfstorage.settings import DEFAULT_REGION_ID
from website.util import api_v2_url

settings = apps.get_app_config('addons_osfstorage')

logger = logging.getLogger(__name__)


class OsfStorageFolderManager(BaseFileNodeManager):

    def get_root(self, target):
        # Get the root folder that the target file belongs to
        content_type = ContentType.objects.get_for_model(target)
        return self.get(target_object_id=target.id, target_content_type=content_type, is_root=True)


class OsfStorageFileNode(BaseFileNode):
    _provider = 'osfstorage'

    @property
    def materialized_path(self):
        sql = """
            WITH RECURSIVE materialized_path_cte(parent_id, GEN_PATH) AS (
              SELECT
                T.parent_id,
                T.name :: TEXT AS GEN_PATH
              FROM %s AS T
              WHERE T.id = %s
              UNION ALL
              SELECT
                T.parent_id,
                (T.name || '/' || R.GEN_PATH) AS GEN_PATH
              FROM materialized_path_cte AS R
                JOIN %s AS T ON T.id = R.parent_id
              WHERE R.parent_id IS NOT NULL
            )
            SELECT gen_path
            FROM materialized_path_cte AS N
            WHERE parent_id IS NULL
            LIMIT 1;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [AsIs(self._meta.db_table), self.pk, AsIs(self._meta.db_table)])
            row = cursor.fetchone()
            if not row:
                return '/'

            path = row[0]
            if not self.is_file:
                path = path + '/'
            return path

    @materialized_path.setter
    def materialized_path(self, val):
        # raise Exception('Cannot set materialized path on OSFStorage as it is computed.')
        logger.warn('Cannot set materialized path on OSFStorage because it\'s computed.')

    @classmethod
    def get(cls, _id, target):
        return cls.objects.get(_id=_id, target_object_id=target.id, target_content_type=ContentType.objects.get_for_model(target))

    @classmethod
    def get_or_create(cls, target, path):
        """Override get or create for osfstorage
        Path is always the _id of the osfstorage filenode.
        Use load here as its way faster than find.
        Just manually assert that node is equal to node.
        """
        inst = cls.load(path.strip('/'))
        if inst and inst.target.id == target.id:
            return inst

        # Dont raise anything a 404 will be raised later
        return cls(target=target, path=path)

    @classmethod
    def get_file_guids(cls, materialized_path, provider, target=None):
        guids = []
        path = materialized_path.strip('/')
        file_obj = cls.load(path)
        if not file_obj:
            file_obj = TrashedFileNode.load(path)

        # At this point, file_obj may be an OsfStorageFile, an OsfStorageFolder, or a
        # TrashedFileNode. TrashedFileNodes do not have *File and *Folder subclasses, since
        # only osfstorage trashes folders. To search for children of TrashFileNodes
        # representing ex-OsfStorageFolders, we will reimplement the `children` method of the
        # Folder class here.
        if not file_obj.is_file:
            children = []
            if isinstance(file_obj, TrashedFileNode):
                children = file_obj.trashed_children.all()
            else:
                children = file_obj.children

            for item in children:
                guids.extend(cls.get_file_guids(item.path, provider, target=target))
        else:
            guid = file_obj.get_guid()
            if guid:
                guids.append(guid._id)

        return sorted(guids)

    @property
    def kind(self):
        return 'file' if self.is_file else 'folder'

    @property
    def path(self):
        """Path is dynamically computed as storedobject.path is stored
        as an empty string to make the unique index work properly for osfstorage
        """
        return '/' + self._id + ('' if self.is_file else '/')

    @property
    def is_checked_out(self):
        return self.checkout is not None

    # overrides BaseFileNode
    @property
    def current_version_number(self):
        return self.versions.count() or 1

    def _check_delete_allowed(self):
        if self.is_preprint_primary:
            raise exceptions.FileNodeIsPrimaryFile()
        if self.is_checked_out:
            raise exceptions.FileNodeCheckedOutError()
        return True

    @property
    def is_preprint_primary(self):
        return getattr(self.target, 'preprint_file', None) == self and not getattr(self.target, '_has_abandoned_preprint', None)

    def delete(self, user=None, parent=None, **kwargs):
        self._path = self.path
        self._materialized_path = self.materialized_path
        return super(OsfStorageFileNode, self).delete(user=user, parent=parent) if self._check_delete_allowed() else None

    def move_under(self, destination_parent, name=None):
        if self.is_preprint_primary:
            if self.target != destination_parent.target or self.provider != destination_parent.provider:
                raise exceptions.FileNodeIsPrimaryFile()
        if self.is_checked_out:
            raise exceptions.FileNodeCheckedOutError()
        return super(OsfStorageFileNode, self).move_under(destination_parent, name)

    def check_in_or_out(self, user, checkout, save=False):
        """
        Updates self.checkout with the requesting user or None,
        iff user has permission to check out file or folder.
        Adds log to self.target if target is a node.


        :param user:        User making the request
        :param checkout:    Either the same user or None, depending on in/out-checking
        :param save:        Whether or not to save the user
        """
        from osf.models import NodeLog  # Avoid circular import

        target = self.target
        if isinstance(target, AbstractNode) and self.is_checked_out and self.checkout != user:
            # Allow project admins to force check in
            if target.has_permission(user, permissions.ADMIN):
                # But don't allow force check in for prereg admin checked out files
                if self.checkout.has_perm('osf.view_prereg') and target.draft_registrations_active.filter(
                        registration_schema__name='Prereg Challenge').exists():
                    raise exceptions.FileNodeCheckedOutError()
            else:
                raise exceptions.FileNodeCheckedOutError()

        if not target.has_permission(user, permissions.WRITE):
            raise exceptions.FileNodeCheckedOutError()

        action = NodeLog.CHECKED_OUT if checkout else NodeLog.CHECKED_IN

        if self.is_checked_out and action == NodeLog.CHECKED_IN or not self.is_checked_out and action == NodeLog.CHECKED_OUT:
            self.checkout = checkout
            if isinstance(target, Loggable):
                target.add_log(
                    action=action,
                    params={
                        'kind': self.kind,
                        'project': target.parent_id,
                        'node': target._id,
                        'urls': {
                            # web_url_for unavailable -- called from within the API, so no flask app
                            'download': '/project/{}/files/{}/{}/?action=download'.format(target._id,
                                                                                          self.provider,
                                                                                          self._id),
                            'view': '/project/{}/files/{}/{}'.format(target._id, self.provider, self._id)},
                        'path': self.materialized_path
                    },
                    auth=Auth(user),
                )

            if save:
                self.save()

    def save(self):
        self._path = ''
        self._materialized_path = ''
        return super(OsfStorageFileNode, self).save()


class OsfStorageFile(OsfStorageFileNode, File):

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

    def touch(self, bearer, version=None, revision=None, **kwargs):
        try:
            return self.get_version(revision or version)
        except ValueError:
            return None

    @property
    def history(self):
        return list(self.versions.values_list('metadata', flat=True))

    @history.setter
    def history(self, value):
        logger.warn('Tried to set history on OsfStorageFile/Folder')

    def serialize(self, include_full=None, version=None):
        ret = super(OsfStorageFile, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path

        version = self.get_version(version)
        earliest_version = self.versions.order_by('created').first()
        ret.update({
            'version': self.versions.count(),
            'md5': version.metadata.get('md5') if version else None,
            'sha256': version.metadata.get('sha256') if version else None,
            'modified': version.created.isoformat() if version else None,
            'created': earliest_version.created.isoformat() if version else None,
        })
        return ret

    def create_version(self, creator, location, metadata=None):
        latest_version = self.get_version()
        version = FileVersion(identifier=self.versions.count() + 1, creator=creator, location=location)

        if latest_version and latest_version.is_duplicate(version):
            return latest_version

        if metadata:
            version.update_metadata(metadata)

        version._find_matching_archive(save=False)

        version.save()
        self.versions.add(version)
        self.save()

        return version

    def get_version(self, version=None, required=False):
        if version is None:
            if self.versions.exists():
                return self.versions.first()
            return None

        try:
            return self.versions.get(identifier=version)
        except FileVersion.DoesNotExist:
            if required:
                raise exceptions.VersionNotFoundError(version)
            return None

    def add_tag_log(self, action, tag, auth):
        if isinstance(self.target, Loggable):
            target = self.target
            params = {
                'urls': {
                    'download': '/{}/files/osfstorage/{}/?action=download'.format(target._id, self._id),
                    'view': '/{}/files/osfstorage/{}/'.format(target._id, self._id)},
                'path': self.materialized_path,
                'tag': tag,
            }
            if isinstance(target, AbstractNode):
                params['parent_node'] = target.parent_id
                params['node'] = target._id

            target.add_log(
                action=action,
                params=params,
                auth=auth,
            )
        else:
            raise NotImplementedError('Cannot add a tag log to a {}'.format(self.target.__class__.__name__))

    def add_tag(self, tag, auth, save=True, log=True):
        from osf.models import Tag, NodeLog  # Prevent import error

        if not self.tags.filter(system=False, name=tag).exists() and not getattr(self.target, 'is_registration', False):
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(name=tag)
            new_tag.save()
            self.tags.add(new_tag)
            if log:
                self.add_tag_log(NodeLog.FILE_TAG_ADDED, tag, auth)
            if save:
                self.save()
            return True
        return False

    def remove_tag(self, tag, auth, save=True, log=True):
        from osf.models import Tag, NodeLog  # Prevent import error
        if getattr(self.target, 'is_registration', False):
            # Can't perform edits on a registration
            raise NodeStateError
        tag_instance = Tag.objects.filter(system=False, name=tag).first()
        if not tag_instance:
            raise InvalidTagError
        elif not self.tags.filter(id=tag_instance.id).exists():
            raise TagNotFoundError
        else:
            self.tags.remove(tag_instance)
            if log:
                self.add_tag_log(NodeLog.FILE_TAG_REMOVED, tag_instance._id, auth)
            if save:
                self.save()
            return True

    def delete(self, user=None, parent=None, **kwargs):
        from website.search import search

        search.update_file(self, delete=True)
        return super(OsfStorageFile, self).delete(user, parent, **kwargs)

    def save(self, skip_search=False, *args, **kwargs):
        from website.search import search

        ret = super(OsfStorageFile, self).save()
        if not skip_search:
            search.update_file(self)
        return ret


class OsfStorageFolder(OsfStorageFileNode, Folder):

    is_root = models.NullBooleanField()

    objects = OsfStorageFolderManager()

    @property
    def is_checked_out(self):
        sql = """
            WITH RECURSIVE is_checked_out_cte(id, parent_id, checkout_id) AS (
              SELECT
                T.id,
                T.parent_id,
                T.checkout_id
              FROM %s AS T
              WHERE T.id = %s
              UNION ALL
              SELECT
                T.id,
                T.parent_id,
                T.checkout_id
              FROM is_checked_out_cte AS R
                JOIN %s AS T ON T.parent_id = R.id
            )
            SELECT N.checkout_id
            FROM is_checked_out_cte as N
            WHERE N.checkout_id IS NOT NULL
            LIMIT 1;
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, [AsIs(self._meta.db_table), self.pk, AsIs(self._meta.db_table)])
            row = cursor.fetchone()

            if row and row[0]:
                return True

        return False

    @property
    def is_preprint_primary(self):
        if hasattr(self.target, 'preprint_file') and self.target.preprint_file:
            for child in self.children.all().prefetch_related('target'):
                if getattr(child.target, 'preprint_file', None):
                    if child.is_preprint_primary:
                        return True
        return False

    def serialize(self, include_full=False, version=None):
        # Versions just for compatibility
        ret = super(OsfStorageFolder, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path
        return ret


class Region(models.Model):
    _id = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=200)
    waterbutler_credentials = EncryptedJSONField(default=dict)
    waterbutler_url = models.URLField(default=website_settings.WATERBUTLER_URL)
    mfr_url = models.URLField(default=website_settings.MFR_SERVER_URL)
    waterbutler_settings = DateTimeAwareJSONField(default=dict)

    def get_absolute_url(self):
        return '{}regions/{}'.format(self.absolute_api_v2_url, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/regions/{}/'.format(self._id)
        return api_v2_url(path)

    class Meta:
        unique_together = ('_id', 'name')


class UserSettings(BaseUserSettings):
    default_region = models.ForeignKey(Region, null=True, on_delete=models.CASCADE)

    def on_add(self):
        default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
        self.default_region = default_region

    def merge(self, user_settings):
        """Merge `user_settings` into this instance"""
        NodeSettings.objects.filter(user_settings=user_settings).update(user_settings=self)

    def set_region(self, region_id):
        try:
            region = Region.objects.get(_id=region_id)
        except Region.DoesNotExist:
            raise ValueError('Region cannot be found.')

        self.default_region = region
        self.save()
        return


class NodeSettings(BaseNodeSettings, BaseStorageAddon):
    # Required overrides
    complete = True
    has_auth = True

    root_node = models.ForeignKey(OsfStorageFolder, null=True, blank=True, on_delete=models.CASCADE)

    region = models.ForeignKey(Region, null=True, on_delete=models.CASCADE)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_name(self):
        return self.root_node.name

    def get_root(self):
        return self.root_node

    def on_add(self):
        if self.root_node:
            return

        creator_user_settings = UserSettings.objects.get(owner=self.owner.creator)
        self.user_settings = creator_user_settings
        self.region_id = creator_user_settings.default_region_id

        # A save is required here to both create and attach the root_node
        # When on_add is called the model that self refers to does not yet exist
        # in the database and thus odm cannot attach foreign fields to it
        self.save(clean=False)
        # Note: The "root" node will always be "named" empty string
        root = OsfStorageFolder(name='', target=self.owner, is_root=True)
        root.save()
        self.root_node = root
        self.save(clean=False)

    def before_fork(self, node, user):
        pass

    def after_fork(self, node, fork, user, save=True):
        clone = self.clone()
        clone.owner = fork
        clone.user_settings = self.user_settings
        clone.region_id = self.region_id

        clone.save()
        if not self.root_node:
            self.on_add()

        clone.root_node = files_utils.copy_files(self.get_root(), clone.owner)
        clone.save()

        return clone, None

    def after_register(self, node, registration, user, save=True):
        clone = self.clone()
        clone.owner = registration
        clone.on_add()
        clone.region_id = self.region_id
        clone.save()

        return clone, None

    def serialize_waterbutler_settings(self):
        return dict(Region.objects.get(id=self.region_id).waterbutler_settings, **{
            'nid': self.owner._id,
            'rootId': self.root_node._id,
            'baseUrl': api_url_for(
                'osfstorage_get_metadata',
                guid=self.owner._id,
                _absolute=True,
                _internal=True
            ),
        })

    def serialize_waterbutler_credentials(self):
        return Region.objects.get(id=self.region_id).waterbutler_credentials

    def create_waterbutler_log(self, auth, action, metadata):
        params = {
            'node': self.owner._id,
            'project': self.owner.parent_id,

            'path': metadata['materialized'],
        }

        if (metadata['kind'] != 'folder'):
            url = self.owner.web_url_for(
                'addon_view_or_download_file',
                guid=self.owner._id,
                path=metadata['path'],
                provider='osfstorage'
            )
            params['urls'] = {'view': url, 'download': url + '?action=download'}

        self.owner.add_log(
            'osf_storage_{0}'.format(action),
            auth=auth,
            params=params
        )
