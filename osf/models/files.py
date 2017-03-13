import logging

from dateutil.parser import parse as parse_date
from django.db import models, connection
from django.db.models import Manager
from django.utils import timezone
from psycopg2._psycopg import AsIs
from typedmodels.models import TypedModel

from osf.models.base import BaseModel, OptionalGuidMixin, ObjectIDMixin
from osf.models.comment import CommentableMixin
from osf.models.validators import validate_location
from osf.modm_compat import Q
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from website.util import api_v2_url

__all__ = (
    'File',
    'Folder',
    'FileVersion',
    'StoredFileNode',
    'TrashedFileNode',
)

PROVIDER_MAP = {}
logger = logging.getLogger(__name__)


class BaseFileNode(TypedModel, CommentableMixin, OptionalGuidMixin, ObjectIDMixin, BaseModel):
    """
        The storage backend for FileNode objects.
        This class should generally not be used or created manually as FileNode
        contains all the helpers required.
        A FileNode wraps a StoredFileNode to provider usable abstraction layer
    """

    # The last time the touch method was called on this FileNode
    last_touched = NonNaiveDateTimeField(null=True, blank=True)
    # A list of dictionaries sorted by the 'modified' key
    # The raw output of the metadata request deduped by etag
    # Add regardless it can be pinned to a version or not
    history = DateTimeAwareJSONField(default=[], blank=True)
    # A concrete version of a FileNode, must have an identifier
    versions = models.ManyToManyField('FileVersion')

    is_deleted = models.BooleanField(default=False)
    node = models.ForeignKey('osf.AbstractNode', blank=True, null=True)
    parent = models.ForeignKey('self', blank=True, null=True, default=None, related_name='child')
    copied_from = models.ForeignKey('osf.StoredFileNode', blank=True, null=True, default=None, related_name='copy_of')

    deleted_on = NonNaiveDateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey('osf.OSFUser', related_name='files_deleted_by', null=True, blank=True)

    provider = models.CharField(max_length=25, blank=False, null=False, db_index=True)

    name = models.TextField(blank=True, null=True)
    _path = models.TextField(blank=True, null=True)  # 1950 on prod
    _materialized_path = models.TextField(blank=True, null=True)  # 482 on staging

    # The User that has this file "checked out"
    # Should only be used for OsfStorage
    checkout = models.ForeignKey('osf.OSFUser', blank=True, null=True)

    class Meta:
        index_together = (
            ('node', 'type', 'provider', '_path'),
            ('node', 'type', 'provider'),
        )

    @property
    def is_file(self):
        # TODO split is file logic into subclasses
        return issubclass(self, File)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

    @property
    def materialized_path(self):
        if self.provider == 'osfstorage':
            # TODO Optimize this.
            sql = """
                WITH RECURSIVE
                    materialized_path_cte(id, parent_id, provider, GEN_DEPTH, GEN_PATH) AS (
                    SELECT
                      sfn.id,
                      sfn.parent_id,
                      sfn.provider,
                      1 :: INT         AS depth,
                      sfn.name :: TEXT AS GEN_PATH
                    FROM "%s" AS sfn
                    WHERE
                      sfn.provider = 'osfstorage' AND
                      sfn.parent_id IS NULL
                    UNION ALL
                    SELECT
                      c.id,
                      c.parent_id,
                      c.provider,
                      p.GEN_DEPTH + 1                       AS GEN_DEPTH,
                      (p.GEN_PATH || '/' || c.name :: TEXT) AS GEN_PATH
                    FROM materialized_path_cte AS p, "%s" AS c
                    WHERE c.parent_id = p.id
                  )
                SELECT gen_path
                FROM materialized_path_cte AS n
                WHERE
                  GEN_DEPTH > 1
                  AND
                  n.id = %s
                LIMIT 1;
            """
            with connection.cursor() as cursor:
                cursor.execute(sql, [AsIs(self._meta.db_table), AsIs(self._meta.db_table), self.pk])
                row = cursor.fetchone()
                if not row:
                    return row
                return row[0]
        else:
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

    def delete(self, **kwargs):
        raise Exception('Dangerzone! Only call delete on wrapped StoredFileNodes')


class StoredFileNode(BaseFileNode):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.base.StoredFileNode'
    modm_query = None
    migration_page_size = 10000
    # /TODO DELETE ME POST MIGRATION]

# TODO Refactor code pointing at FileNode to point to StoredFileNode
FileNode = StoredFileNode


class File(StoredFileNode):
    pass


class Folder(StoredFileNode):
    pass


class TrashedFileNode(BaseFileNode):
    pass


class TrashedFile(TrashedFileNode):
    pass


class TrashedFolder(TrashedFileNode):
    pass


class ProviderMixinManager(Manager):
    def get_queryset(self):
        qs = super(ProviderMixinManager, self).get_queryset()
        if self.model.provider is None:
            raise NotImplementedError('ProviderMixin subclasses must implement a provider property.')
        return qs.filter(provider=self.model.provider)


class ProviderMixin(object):
    provider = None
    objects = ProviderMixinManager()


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
