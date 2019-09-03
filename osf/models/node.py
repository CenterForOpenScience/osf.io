import functools
import itertools
import logging
import re
import urlparse
import warnings
import httplib

import bson
from django.db.models import Q
from dirtyfields import DirtyFieldsMixin
from django.apps import apps
from django_bulk_update.helper import bulk_update
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.fields import GenericRelation
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db import models, connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from keen import scoped_keys
from psycopg2._psycopg import AsIs
from typedmodels.models import TypedModel, TypedModelManager
from include import IncludeManager
from guardian.models import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from guardian.shortcuts import get_objects_for_user, get_groups_with_perms, get_group_perms

from framework import status
from framework.auth import oauth_scopes
from framework.celery_tasks.handlers import enqueue_task, get_task_from_queue
from framework.exceptions import PermissionsError, HTTPError
from framework.sentry import log_exception
from osf.exceptions import (InvalidTagError, NodeStateError,
                            TagNotFoundError, UserNotAffiliatedError)
from osf.models.contributor import Contributor
from osf.models.collection import CollectionSubmission

from osf.models.identifiers import Identifier, IdentifierMixin
from osf.models.licenses import NodeLicenseRecord
from osf.models.mixins import (AddonModelMixin, CommentableMixin, Loggable, ContributorMixin, GuardianMixin,
                               NodeLinkMixin, Taggable, TaxonomizableMixin, SpamOverrideMixin)
from osf.models.node_relation import NodeRelation
from osf.models.nodelog import NodeLog
from osf.models.sanctions import RegistrationApproval
from osf.models.private_link import PrivateLink
from osf.models.tag import Tag
from osf.models.user import OSFUser
from osf.models.validators import validate_title, validate_doi
from framework.auth.core import Auth
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.requests import get_request_and_user_id, string_type_request_headers
from osf.utils import sanitize
from website import language, settings
from website.citations.utils import datetime_to_csl
from website.project.licenses import set_license
from website.project import signals as project_signals
from website.project import tasks as node_tasks
from website.project.model import NodeUpdateError
from website.identifiers.tasks import update_doi_metadata_on_change
from website.identifiers.clients import DataCiteClient
from osf.utils.permissions import (
    ADMIN,
    ADMIN_NODE,
    CONTRIB_PERMISSIONS,
    CREATOR_PERMISSIONS,
    PERMISSIONS,
    READ,
    READ_NODE,
    WRITE
)
from website.util import api_url_for, api_v2_url, web_url_for
from .base import BaseModel, GuidMixin, GuidMixinQuerySet
from api.caching.tasks import update_storage_usage
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache


logger = logging.getLogger(__name__)


class AbstractNodeQuerySet(GuidMixinQuerySet):

    def get_roots(self):
        return self.filter(id__in=self.exclude(type='osf.collection').exclude(type='osf.quickfilesnode').values_list('root_id', flat=True))

    def get_children(self, root, active=False, include_root=False):
        # If `root` is a root node, we can use the 'descendants' related name
        # rather than doing a recursive query
        if root.id == root.root_id:
            query = root.descendants.all() if include_root else root.descendants.exclude(id=root.id)
            if active:
                query = query.filter(is_deleted=False)
            return query
        else:
            sql = """
                WITH RECURSIVE descendants AS (
                SELECT
                    parent_id,
                    child_id,
                    1 AS LEVEL,
                    ARRAY[parent_id] as pids
                FROM %s
                %s
                WHERE is_node_link IS FALSE AND parent_id = %s %s
                UNION ALL
                SELECT
                    d.parent_id,
                    s.child_id,
                    d.level + 1,
                    d.pids || s.parent_id
                FROM descendants AS d
                    JOIN %s AS s
                    ON d.child_id = s.parent_id
                WHERE s.is_node_link IS FALSE AND %s = ANY(pids)
                ) SELECT array_agg(DISTINCT child_id)
                FROM descendants
                WHERE parent_id = %s;
            """
            with connection.cursor() as cursor:
                node_relation_table = AsIs(NodeRelation._meta.db_table)
                cursor.execute(sql, [
                    node_relation_table,
                    AsIs('LEFT JOIN osf_abstractnode ON {}.child_id = osf_abstractnode.id'.format(node_relation_table) if active else ''),
                    root.pk,
                    AsIs('AND osf_abstractnode.is_deleted IS FALSE' if active else ''),
                    node_relation_table,
                    root.pk,
                    root.pk])
                row = cursor.fetchone()[0]
                if not row:
                    return AbstractNode.objects.filter(id=root.pk) if include_root else AbstractNode.objects.none()
                if include_root:
                    row.append(root.pk)
                return AbstractNode.objects.filter(id__in=row)

    def can_view(self, user=None, private_link=None):
        qs = self.filter(is_public=True)

        if private_link is not None:
            if isinstance(private_link, PrivateLink):
                private_link = private_link.key
            if not isinstance(private_link, basestring):
                raise TypeError('"private_link" must be either {} or {}. Got {!r}'.format(str, PrivateLink, private_link))

            qs |= self.filter(private_links__is_deleted=False, private_links__key=private_link)

        if user is not None and not isinstance(user, AnonymousUser):
            read_user_query = get_objects_for_user(user, READ_NODE, self, with_superuser=False)
            qs |= read_user_query
            qs |= self.extra(where=["""
                "osf_abstractnode".id in (
                    WITH RECURSIVE implicit_read AS (
                        SELECT N.id as node_id
                        FROM osf_abstractnode as N, auth_permission as P, osf_nodegroupobjectpermission as G, osf_osfuser_groups as UG
                        WHERE P.codename = 'admin_node'
                        AND G.permission_id = P.id
                        AND UG.osfuser_id = %s
                        AND G.group_id = UG.group_id
                        AND G.content_object_id = N.id
                        AND N.type = 'osf.node'
                    UNION ALL
                        SELECT "osf_noderelation"."child_id"
                        FROM "implicit_read"
                        LEFT JOIN "osf_noderelation" ON "osf_noderelation"."parent_id" = "implicit_read"."node_id"
                        WHERE "osf_noderelation"."is_node_link" IS FALSE
                    ) SELECT * FROM implicit_read
                )
            """], params=(user.id, ))
        return qs.filter(is_deleted=False)


class AbstractNodeManager(TypedModelManager, IncludeManager):

    def get_queryset(self):
        qs = AbstractNodeQuerySet(self.model, using=self._db)
        # Filter by typedmodels type
        return self._filter_by_type(qs)

    # AbstractNodeQuerySet methods

    def get_roots(self):
        return self.get_queryset().get_roots()

    def get_children(self, root, active=False, include_root=False):
        return self.get_queryset().get_children(root, active=active, include_root=include_root)

    def can_view(self, user=None, private_link=None):
        return self.get_queryset().can_view(user=user, private_link=private_link)

    def get_nodes_for_user(self, user, permission=READ_NODE, base_queryset=None, include_public=False):
        """
        Return all AbstractNodes that the user has permissions to - either through contributorship or group membership.
        - similar to guardian.get_objects_for_user(self, READ_NODE, AbstractNode, with_superuser=False).  If include_public is True,
        queryset is expanded to include public nodes.

        :param User user: User object to check
        :param permission: Permission string to check, official perm, i.e. 'read_node', 'write_node', 'admin_node'
        :param base_queryset: If filtering on a smaller queryset is desired, pass in a starting queryset
        :param include_public: If True, will include public nodes in query that user may not have explicit perms to
        :returns node queryset that the user has perms to
        """
        OSFUserGroup = apps.get_model('osf', 'osfuser_groups')
        if base_queryset is None:
            base_queryset = self

        if permission not in PERMISSIONS:
            raise ValueError('Permission must be one of {}, {}, or {}.'.format(PERMISSIONS[0], PERMISSIONS[1], PERMISSIONS[2]))

        nodes = base_queryset.filter(is_deleted=False)
        permission_object_id = Permission.objects.get(codename=permission).id
        user_groups = OSFUserGroup.objects.filter(osfuser_id=user.id if user else None).values_list('group_id', flat=True)
        node_groups = NodeGroupObjectPermission.objects.filter(group_id__in=user_groups, permission_id=permission_object_id).values_list('content_object_id', flat=True)
        query = Q(id__in=node_groups)
        if include_public:
            query |= Q(is_public=True)
        return nodes.filter(query)


class AbstractNode(DirtyFieldsMixin, TypedModel, AddonModelMixin, IdentifierMixin, GuardianMixin,
                   NodeLinkMixin, CommentableMixin, SpamOverrideMixin, TaxonomizableMixin,
                   ContributorMixin, Taggable, Loggable, GuidMixin, BaseModel):
    """
    All things that inherit from AbstractNode will appear in
    the same table and will be differentiated by the `type` column.
    """

    #: Whether this is a pointer or not
    primary = True
    settings_type = 'node'  # Needed for addons

    FIELD_ALIASES = {
        # TODO: Find a better way
        '_id': 'guids___id',
        'nodes': '_nodes',
        'contributors': '_contributors',
    }

    CATEGORY_MAP = {
        'analysis': 'Analysis',
        'communication': 'Communication',
        'data': 'Data',
        'hypothesis': 'Hypothesis',
        'instrumentation': 'Instrumentation',
        'methods and measures': 'Methods and Measures',
        'procedure': 'Procedure',
        'project': 'Project',
        'software': 'Software',
        'other': 'Other',
        '': 'Uncategorized',
    }

    # Node fields that trigger an update to Solr on save
    SEARCH_UPDATE_FIELDS = {
        'title',
        'category',
        'description',
        'is_fork',
        'retraction',
        'embargo',
        'is_public',
        'is_deleted',
        'node_license',
    }

    # Node fields that trigger an identifier update on save
    IDENTIFIER_UPDATE_FIELDS = {
        'title',
        'description',
        'is_public',
        'contributors',
        'is_deleted',
        'node_license'
    }

    # Node fields that trigger a check to the spam filter on save
    SPAM_CHECK_FIELDS = {
        'title',
        'description',
        'addons_forward_node_settings__url'  # the often spammed redirect URL
    }

    # Fields that are writable by Node.update
    WRITABLE_WHITELIST = [
        'title',
        'description',
        'category',
        'is_public',
        'node_license',
    ]

    # Named constants
    PRIVATE = 'private'
    PUBLIC = 'public'

    LICENSE_QUERY = re.sub(r'\s+', ' ', """WITH RECURSIVE ascendants AS (
            SELECT
                N.node_license_id,
                R.parent_id
            FROM "{noderelation}" AS R
                JOIN "{abstractnode}" AS N ON N.id = R.parent_id
            WHERE R.is_node_link IS FALSE
                AND R.child_id = %s
        UNION ALL
            SELECT
                N.node_license_id,
                R.parent_id
            FROM ascendants AS D
                JOIN "{noderelation}" AS R ON D.parent_id = R.child_id
                JOIN "{abstractnode}" AS N ON N.id = R.parent_id
            WHERE R.is_node_link IS FALSE
            AND D.node_license_id IS NULL
    ) SELECT {fields} FROM "{nodelicenserecord}"
    WHERE id = (SELECT node_license_id FROM ascendants WHERE node_license_id IS NOT NULL) LIMIT 1;""")

    affiliated_institutions = models.ManyToManyField('Institution', related_name='nodes')
    category = models.CharField(max_length=255,
                                choices=CATEGORY_MAP.items(),
                                blank=True,
                                default='')
    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    # TODO: Can this be a reference instead of data?
    child_node_subscriptions = DateTimeAwareJSONField(default=dict, blank=True)
    _contributors = models.ManyToManyField(OSFUser,
                                           through=Contributor,
                                           related_name='nodes')

    creator = models.ForeignKey(OSFUser,
                                db_index=True,
                                related_name='nodes_created',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    deleted_date = NonNaiveDateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    file_guid_to_share_uuids = DateTimeAwareJSONField(default=dict, blank=True)
    forked_date = NonNaiveDateTimeField(db_index=True, null=True, blank=True)
    forked_from = models.ForeignKey('self',
                                    related_name='forks',
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    is_fork = models.BooleanField(default=False, db_index=True)
    is_public = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    access_requests_enabled = models.NullBooleanField(default=True, db_index=True)
    node_license = models.ForeignKey('NodeLicenseRecord', related_name='nodes',
                                     on_delete=models.SET_NULL, null=True, blank=True)

    custom_citation = models.TextField(blank=True, null=True)

    # One of 'public', 'private'
    # TODO: Add validator
    comment_level = models.CharField(default='public', max_length=10)

    root = models.ForeignKey('AbstractNode',
                                default=None,
                                related_name='descendants',
                                on_delete=models.SET_NULL, null=True, blank=True)

    _nodes = models.ManyToManyField('AbstractNode',
                                    through=NodeRelation,
                                    through_fields=('parent', 'child'),
                                    related_name='parent_nodes')

    files = GenericRelation('osf.OsfStorageFile', object_id_field='target_object_id', content_type_field='target_content_type')
    groups = {
        'read': ('read_node',),
        'write': ('read_node', 'write_node',),
        'admin': ('read_node', 'write_node', 'admin_node',)
    }
    group_format = 'node_{self.id}_{group}'

    article_doi = models.CharField(max_length=128,
                                        validators=[validate_doi],
                                        null=True, blank=True)

    class Meta:
        base_manager_name = 'objects'
        index_together = (('is_public', 'is_deleted', 'type'))
        permissions = (
            ('view_node', 'Can view node details'),
            ('read_node', 'Can read the node'),
            ('write_node', 'Can edit the node'),
            ('admin_node', 'Can manage the node'),
        )

    objects = AbstractNodeManager()

    @cached_property
    def parent_node(self):
        try:
            node_rel = self._parents.filter(is_node_link=False)[0]
        except IndexError:
            node_rel = None
        if node_rel:
            parent = node_rel.parent
            if parent:
                return parent
        return None

    @property
    def nodes(self):
        """Return queryset of nodes."""
        return self.get_nodes()

    @property
    def node_ids(self):
        return list(self._nodes.all().values_list('guids___id', flat=True))

    @property
    def linked_from(self):
        """Return the nodes that have linked to this node."""
        return self.parent_nodes.filter(node_relations__is_node_link=True)

    @property
    def linked_from_collections(self):
        """Return the collections that have linked to this node."""
        return self.linked_from.filter(type='osf.collection')

    def get_nodes(self, **kwargs):
        """Return list of children nodes. ``kwargs`` are used to filter against
        children. In addition `is_node_link=<bool>` can be passed to filter against
        node links.
        """
        # Prepend 'child__' to kwargs for filtering
        filter_kwargs = {}
        if 'is_node_link' in kwargs:
            filter_kwargs['is_node_link'] = kwargs.pop('is_node_link')
        for key, val in kwargs.items():
            filter_kwargs['child__{}'.format(key)] = val
        node_relations = (NodeRelation.objects.filter(parent=self, **filter_kwargs)
                        .select_related('child')
                        .order_by('_order'))
        return [each.child for each in node_relations]

    @property
    def linked_nodes(self):
        child_pks = NodeRelation.objects.filter(
            parent=self,
            is_node_link=True
        ).select_related('child').values_list('child', flat=True)
        return self._nodes.filter(pk__in=child_pks)

    # permissions = Permissions are now on contributors
    piwik_site_id = models.IntegerField(null=True, blank=True)
    suspended = models.BooleanField(default=False, db_index=True)

    # The node (if any) used as a template for this node's creation
    template_node = models.ForeignKey('self',
                                      related_name='templated_from',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True)
    title = models.TextField(
        validators=[validate_title]
    )  # this should be a charfield but data from mongo didn't fit in 255
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DateTimeAwareJSONField(default=dict, blank=True)

    identifiers = GenericRelation(Identifier, related_query_name='nodes')

    keenio_read_key = models.CharField(max_length=1000, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        self._parent = kwargs.pop('parent', None)
        self._is_templated_clone = False
        super(AbstractNode, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return ('(title={self.title!r}, category={self.category!r}) '
                'with guid {self._id!r}').format(self=self)

    @property
    def is_registration(self):
        """For v1 compat."""
        return False

    @property
    def is_quickfiles(self):
        return False

    @property
    def is_original(self):
        return not self.is_registration and not self.is_fork

    @property
    def is_collected(self):
        """is included in a collection"""
        return self.collecting_metadata_qs.exists()

    @property
    def collecting_metadata_qs(self):
        return CollectionSubmission.objects.filter(
            guid=self.guids.first(),
            collection__provider__isnull=False,
            collection__deleted__isnull=True,
            collection__is_bookmark_collection=False)

    @property
    def collecting_metadata_list(self):
        return list(self.collecting_metadata_qs)

    @property
    def has_linked_published_preprints(self):
        # Node holds supplemental material for published preprint(s)
        Preprint = apps.get_model('osf.Preprint')
        return self.preprints.filter(Preprint.objects.no_user_query).exists()

    @property
    def is_collection(self):
        """For v1 compat"""
        return False

    @property  # TODO Separate out for submodels
    def absolute_api_v2_url(self):
        if self.is_registration:
            path = '/registrations/{}/'.format(self._id)
            return api_v2_url(path)
        if self.is_collection:
            path = '/collections/{}/'.format(self._id)
            return api_v2_url(path)
        path = '/nodes/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def absolute_url(self):
        if not self.url:
            return None
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def deep_url(self):
        return '/project/{}/'.format(self._primary_key)

    @property
    def sanction(self):
        """For v1 compat. Registration has the proper implementation of this property."""
        return None

    @property
    def is_retracted(self):
        """For v1 compat."""
        return False

    @property
    def is_pending_registration(self):
        """For v1 compat."""
        return False

    @property
    def is_pending_retraction(self):
        """For v1 compat."""
        return False

    @property
    def is_pending_embargo(self):
        """For v1 compat."""
        return False

    @property
    def is_embargoed(self):
        """For v1 compat."""
        return False

    @property
    def archiving(self):
        """For v1 compat."""
        return False

    @property
    def embargo_end_date(self):
        """For v1 compat."""
        return False

    @property
    def forked_from_guid(self):
        if self.forked_from:
            return self.forked_from._id
        return None

    @property
    def linked_nodes_self_url(self):
        return self.absolute_api_v2_url + 'relationships/linked_nodes/'

    @property
    def linked_registrations_self_url(self):
        return self.absolute_api_v2_url + 'relationships/linked_registrations/'

    @property
    def linked_nodes_related_url(self):
        return self.absolute_api_v2_url + 'linked_nodes/'

    @property
    def linked_registrations_related_url(self):
        return self.absolute_api_v2_url + 'linked_registrations/'

    @property
    def institutions_url(self):
        return self.absolute_api_v2_url + 'institutions/'

    @property
    def institutions_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/institutions/'

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'nodes'

    @property
    def root_target_page(self):
        """The comment page type associated with Nodes."""
        Comment = apps.get_model('osf.Comment')
        return Comment.OVERVIEW

    def belongs_to_node(self, node_id):
        """Check whether this node matches the specified node."""
        return self._id == node_id

    @property
    def category_display(self):
        """The human-readable representation of this node's category."""
        return settings.NODE_CATEGORY_MAP[self.category]

    @property
    def url(self):
        return '/{}/'.format(self._primary_key)

    @property
    def api_url(self):
        if not self.url:
            logger.error('Node {0} has a parent that is not a project'.format(self._id))
            return None
        return '/api/v1{0}'.format(self.deep_url)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def nodes_active(self):
        return self._nodes.filter(is_deleted=False)

    def web_url_for(self, view_name, _absolute=False, _guid=False, *args, **kwargs):
        return web_url_for(view_name, pid=self._primary_key,
                           _absolute=_absolute, _guid=_guid, *args, **kwargs)

    def api_url_for(self, view_name, _absolute=False, *args, **kwargs):
        return api_url_for(view_name, pid=self._primary_key, _absolute=_absolute, *args, **kwargs)

    @property
    def project_or_component(self):
        # The distinction is drawn based on whether something has a parent node, rather than by category
        return 'project' if not self.parent_node else 'component'

    @property
    def templated_list(self):
        return self.templated_from.filter(is_deleted=False)

    @property
    def draft_registrations_active(self):
        DraftRegistration = apps.get_model('osf.DraftRegistration')
        return DraftRegistration.objects.filter(
            models.Q(branched_from=self) &
            models.Q(deleted__isnull=True) &
            (models.Q(registered_node=None) | models.Q(registered_node__is_deleted=True))
        )

    @property
    def has_active_draft_registrations(self):
        return self.draft_registrations_active.exists()

    @property
    def csl(self):  # formats node information into CSL format for citation parsing
        """a dict in CSL-JSON schema

        For details on this schema, see:
            https://github.com/citation-style-language/schema#csl-json-schema
        """
        csl = {
            'id': self._id,
            'title': sanitize.unescape_entities(self.title),
            'author': [
                contributor.csl_name(self._id)  # method in auth/model.py which parses the names of authors
                for contributor in self.visible_contributors
            ],
            'publisher': 'OSF',
            'type': 'webpage',
            'URL': self.display_absolute_url,
        }

        doi = self.get_identifier_value('doi')
        if doi:
            csl['DOI'] = doi

        if self.logs.exists():
            csl['issued'] = datetime_to_csl(self.logs.latest().date)

        return csl

    @property
    def should_request_identifiers(self):
        return not self.all_tags.filter(name='qatest').exists()

    @classmethod
    def bulk_update_search(cls, nodes, index=None):
        from website import search
        try:
            serialize = functools.partial(search.search.update_node, index=index, bulk=True, async_update=False)
            search.search.bulk_update_nodes(serialize, nodes, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def update_search(self):
        from website import search

        try:
            search.search.update_node(self, bulk=False, async_update=True)
            if self.is_collected and self.is_public:
                search.search.update_collected_metadata(self._id)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def delete_search_entry(self):
        from website import search
        try:
            search.search.delete_node(self)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def is_affiliated_with_institution(self, institution):
        return self.affiliated_institutions.filter(id=institution.id).exists()

    @classmethod
    def find_by_institutions(cls, inst, query=None):
        return inst.nodes.filter(query) if query else inst.nodes.all()

    def _is_embargo_date_valid(self, end_date):
        now = timezone.now()
        if (end_date - now) >= settings.EMBARGO_END_DATE_MIN:
            if (end_date - now) <= settings.EMBARGO_END_DATE_MAX:
                return True
        return False

    def add_affiliated_institution(self, inst, user, save=False, log=True):
        if not user.is_affiliated_with_institution(inst):
            raise UserNotAffiliatedError('User is not affiliated with {}'.format(inst.name))
        if not self.is_affiliated_with_institution(inst):
            self.affiliated_institutions.add(inst)
            self.update_search()
        if log:
            NodeLog = apps.get_model('osf.NodeLog')

            self.add_log(
                action=NodeLog.AFFILIATED_INSTITUTION_ADDED,
                params={
                    'node': self._primary_key,
                    'institution': {
                        'id': inst._id,
                        'name': inst.name
                    }
                },
                auth=Auth(user)
            )

    def remove_affiliated_institution(self, inst, user, save=False, log=True):
        if self.is_affiliated_with_institution(inst):
            self.affiliated_institutions.remove(inst)
            if log:
                self.add_log(
                    action=NodeLog.AFFILIATED_INSTITUTION_REMOVED,
                    params={
                        'node': self._primary_key,
                        'institution': {
                            'id': inst._id,
                            'name': inst.name
                        }
                    },
                    auth=Auth(user)
                )
            if save:
                self.save()
            self.update_search()
            return True
        return False

    def can_view(self, auth):
        if auth and getattr(auth.private_link, 'anonymous', False):
            return auth.private_link.nodes.filter(pk=self.pk).exists()

        if not auth and not self.is_public:
            return False

        return (self.is_public or
                (auth.user and self.has_permission(auth.user, READ)) or
                auth.private_key in self.private_link_keys_active or
                self.is_admin_parent(auth.user))

    def can_edit(self, auth=None, user=None):
        """Return if a user is authorized to edit this node.
        Must specify one of (`auth`, `user`).

        :param Auth auth: Auth object to check
        :param User user: User object to check
        :returns: Whether user has permission to edit this node.
        """
        if not auth and not user:
            raise ValueError('Must pass either `auth` or `user`')
        if auth and user:
            raise ValueError('Cannot pass both `auth` and `user`')
        user = user or auth.user
        if auth:
            is_api_node = auth.api_node == self
        else:
            is_api_node = False
        return (
            (user and self.has_permission(user, WRITE)) or is_api_node
        )

    def add_osf_group(self, group, permission=WRITE, auth=None):
        if auth and not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Must be an admin to add an OSF Group.')
        group.add_group_to_node(self, permission, auth)

    def update_osf_group(self, group, permission=WRITE, auth=None):
        if auth and not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Must be an admin to add an OSF Group.')
        group.update_group_permissions_to_node(self, permission, auth)

    def remove_osf_group(self, group, auth=None):
        if auth and not (self.has_permission(auth.user, ADMIN) or group.has_permission(auth.user, 'manage')):
            raise PermissionsError('Must be an admin or an OSF Group manager to remove an OSF Group.')
        group.remove_group_from_node(self, auth)

    @property
    def osf_groups(self):
        """Returns a queryset of OSF Groups whose members have some permission to the node
        """
        from osf.models.osf_group import OSFGroupGroupObjectPermission, OSFGroup

        member_groups = get_groups_with_perms(self).filter(name__icontains='osfgroup')
        return OSFGroup.objects.filter(id__in=OSFGroupGroupObjectPermission.objects.filter(group_id__in=member_groups).values_list('content_object_id'))

    def get_osf_groups_with_perms(self, permission):
        """Returns a queryset of OSF Groups whose members have the specified permission to the node
        """
        from osf.models.osf_group import OSFGroup
        from osf.models.node import NodeGroupObjectPermission
        try:
            perm_id = Permission.objects.get(codename=permission + '_node').id
        except Permission.DoesNotExist:
            raise ValueError('Specified permission does not exist.')
        member_groups = NodeGroupObjectPermission.objects.filter(
            permission_id=perm_id, content_object_id=self.id
        ).filter(
            group__name__icontains='osfgroup'
        ).values_list(
            'group_id', flat=True
        )
        return OSFGroup.objects.filter(osfgroupgroupobjectpermission__group_id__in=member_groups)

    def get_aggregate_logs_query(self, auth):
        return (
            (
                Q(node_id__in=list(Node.objects.get_children(self).can_view(user=auth.user, private_link=auth.private_link).values_list('id', flat=True)) + [self.id])
            ) & Q(should_hide=False)
        )

    def get_aggregate_logs_queryset(self, auth):
        query = self.get_aggregate_logs_query(auth)
        return NodeLog.objects.filter(query).order_by('-date').include(
            'node__guids', 'user__guids', 'original_node__guids', limit_includes=10
        )

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_permissions(self, user):
        # Overrides guardian mixin - doesn't return view_node perms, and
        # returns readable perms instead of literal perms
        if isinstance(user, AnonymousUser):
            return []
        # Returns perms either through contributorship or group membership
        user_perms = sorted(set(get_group_perms(user, self)).intersection(PERMISSIONS), key=PERMISSIONS.index)
        return [CONTRIB_PERMISSIONS[perm] for perm in user_perms]

    def has_permission_on_children(self, user, permission):
        """Checks if the given user has a given permission on any child nodes
            that are not registrations or deleted
        """
        if self.has_permission(user, permission):
            return True
        for node in self.nodes_primary.filter(is_deleted=False):
            if node.has_permission_on_children(user, permission):
                return True
        return False

    def is_admin_parent(self, user, include_group_admin=True):
        """
        :param user: OSFUser to check for admin permissions
        :param bool include_group_admin: Check if a user is an admin on the parent project via a group.
                                    Useful for checking parent permissions for non-group actions like registrations.
        :return: bool Does the user have admin permissions on this object or its parents?
        """
        if self.has_permission(user, ADMIN, check_parent=False):
            ret = True
            if not include_group_admin and not self.is_contributor(user):
                ret = False
            return ret
        parent = self.parent_node
        if parent:
            return parent.is_admin_parent(user, include_group_admin=include_group_admin)
        return False

    def find_readable_descendants(self, auth):
        """ Returns a generator of first descendant node(s) readable by <user>
        in each descendant branch.
        """
        new_branches = []
        for node in self.nodes_primary.filter(is_deleted=False):
            if node.can_view(auth):
                yield node
            else:
                new_branches.append(node)

        for bnode in new_branches:
            for node in bnode.find_readable_descendants(auth):
                yield node

    @property
    def parents(self):
        if self.parent_node:
            return [self.parent_node] + self.parent_node.parents
        return []

    def get_users_with_perm(self, permission):
        # Returns queryset of all User objects with a specific permission for the given node
        # Can either have these perms through contributorship or group membership.
        # Implicit admin not included here, and superusers not included.
        if permission not in self.groups:
            return False

        perm = Permission.objects.get(codename='{}_node'.format(permission))
        node_group_objects = NodeGroupObjectPermission.objects.filter(permission_id=perm.id,
                                                            content_object_id=self.id).values_list('group_id', flat=True)
        return OSFUser.objects.filter(groups__id__in=node_group_objects).distinct('id', 'family_name')

    @property
    def parent_admin_contributor_ids(self):
        """
        Contributors who have admin permissions on a parent (excludes group members),
        and by default, don't have perms on the current node

        """
        return self._get_admin_contributor_ids()

    def _get_admin_contributor_ids(self, include_self=False):
        def get_admin_contributor_ids(node):
            return node.get_group(ADMIN).user_set.filter(is_active=True).values_list('guids___id', flat=True)
        contributor_ids = set(self.contributors.values_list('guids___id', flat=True))
        admin_ids = set(get_admin_contributor_ids(self)) if include_self else set()
        for parent in self.parents:
            admins = get_admin_contributor_ids(parent)
            admin_ids.update(set(admins).difference(contributor_ids))
        return admin_ids

    @property
    def parent_admin_contributors(self):
        """
        Returns node contributors who are admins on the parent node and not the current
        node (excludes group members)
        """
        return OSFUser.objects.filter(
            guids___id__in=self.parent_admin_contributor_ids
        ).order_by('family_name')

    @property
    def parent_admin_user_ids(self):
        return self._get_admin_user_ids()

    def _get_admin_user_ids(self, include_self=False):
        def get_admin_user_ids(node):
            return node.get_users_with_perm(ADMIN).values_list('guids___id', flat=True)

        contributor_ids = set(self.get_users_with_perm(READ).values_list('guids___id', flat=True))
        admin_ids = set(get_admin_user_ids(self)) if include_self else set()
        for parent in self.parents:
            admins = get_admin_user_ids(parent)
            admin_ids.update(set(admins).difference(contributor_ids))
        return admin_ids

    @property
    def parent_admin_users(self):
        """
        Returns users who are admins on the parent node (and not the current node)

        Includes contributors and members of OSF Groups
        """
        return OSFUser.objects.filter(
            guids___id__in=self.parent_admin_user_ids
        ).order_by('family_name')

    @property
    def contributors_and_group_members(self):
        """
        Returns a queryset of all users who are either contributors
        on the node, or have permission through OSFGroup membership
        """
        return self.get_users_with_perm(READ)

    @property
    def contributor_email_template(self):
        return 'default'

    @property
    def registrations_all(self):
        """For v1 compat."""
        return self.registrations.all()

    @property
    def osfstorage_region(self):
        from addons.osfstorage.models import Region
        osfs_settings = self._settings_model('osfstorage')
        region_subquery = osfs_settings.objects.filter(owner=self.id).values('region_id')
        return Region.objects.get(id=region_subquery)

    @property
    def parent_id(self):
        if hasattr(self, 'annotated_parent_id'):
            # If node has been annotated with "annotated_parent_id"
            # in a queryset, use that value.  Otherwise, fetch the parent_node guid.
            return self.annotated_parent_id
        else:
            if self.parent_node:
                return self.parent_node._id
            return None

    @property
    def license(self):
        if self.node_license_id:
            return self.node_license
        with connection.cursor() as cursor:
            cursor.execute(self.LICENSE_QUERY.format(
                abstractnode=AbstractNode._meta.db_table,
                noderelation=NodeRelation._meta.db_table,
                nodelicenserecord=NodeLicenseRecord._meta.db_table,
                fields=', '.join('"{}"."{}"'.format(NodeLicenseRecord._meta.db_table, f.column) for f in NodeLicenseRecord._meta.concrete_fields)
            ), [self.id])
            res = cursor.fetchone()
            if res:
                return NodeLicenseRecord.from_db(self._state.db, None, res)
        return None

    @property
    def all_tags(self):
        """Return a queryset containing all of this node's tags (incl. system tags)."""
        # Tag's default manager only returns non-system tags, so we can't use self.tags
        return Tag.all_tags.filter(abstractnode_tagged=self)

    @property
    def system_tags(self):
        """The system tags associated with this node. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.all_tags.filter(system=True).values_list('name', flat=True)

    # Override Taggable
    def add_tag_log(self, tag, auth):
        self.add_log(
            action=NodeLog.TAG_ADDED,
            params={
                'parent_node': self.parent_id,
                'node': self._id,
                'tag': tag.name
            },
            auth=auth,
            save=False
        )

    # Override Taggable
    def on_tag_added(self, tag):
        self.update_search()
        node_tasks.update_node_share(self)

    def remove_tag(self, tag, auth, save=True):
        if not tag:
            raise InvalidTagError
        elif not self.tags.filter(name=tag).exists():
            raise TagNotFoundError
        else:
            tag_obj = Tag.objects.get(name=tag)
            self.tags.remove(tag_obj)
            self.add_log(
                action=NodeLog.TAG_REMOVED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._id,
                    'tag': tag,
                },
                auth=auth,
                save=False,
            )
            if save:
                self.save()
            self.update_search()
            node_tasks.update_node_share(self)

            return True

    def remove_tags(self, tags, auth, save=True):
        """
        Unlike remove_tag, this optimization method assumes that the provided
        tags are already present on the node.
        """
        if not tags:
            raise InvalidTagError

        for tag in tags:
            tag_obj = Tag.objects.get(name=tag)
            self.tags.remove(tag_obj)
            self.add_log(
                action=NodeLog.TAG_REMOVED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._id,
                    'tag': tag,
                },
                auth=auth,
                save=False,
            )
        if save:
            self.save()
        self.update_search()
        node_tasks.update_node_share(self)

        return True

    def set_visible(self, user, visible, log=True, auth=None, save=False):
        if not self.is_contributor(user):
            raise ValueError(u'User {0} not in contributors'.format(user))
        if visible and not Contributor.objects.filter(node=self, user=user, visible=True).exists():
            Contributor.objects.filter(node=self, user=user, visible=False).update(visible=True)
        elif not visible and Contributor.objects.filter(node=self, user=user, visible=True).exists():
            if Contributor.objects.filter(node=self, visible=True).count() == 1:
                raise ValueError('Must have at least one visible contributor')
            Contributor.objects.filter(node=self, user=user, visible=True).update(visible=False)
        else:
            return
        message = (
            NodeLog.MADE_CONTRIBUTOR_VISIBLE
            if visible
            else NodeLog.MADE_CONTRIBUTOR_INVISIBLE
        )
        if log:
            self.add_log(
                message,
                params={
                    'parent': self.parent_id,
                    'node': self._id,
                    'contributors': [user._id],
                },
                auth=auth,
                save=False,
            )
        if save:
            self.save()

    @property
    def log_class(self):
        # Override for ContributorMixin
        return NodeLog

    @property
    def contributor_class(self):
        # Override for ContributorMixin
        return Contributor

    @property
    def contributor_kwargs(self):
        # Override for ContributorMixin
        return {'node': self}

    @property
    def log_params(self):
        # Override for ContributorMixin
        return {
            'project': self.parent_id,
            'node': self._primary_key,
        }

    @property
    def order_by_contributor_field(self):
        # Needed for Contributor Mixin
        return 'contributor___order'

    @property
    def state_error(self):
        # Override for ContributorMixin
        return NodeStateError

    def get_spam_fields(self, saved_fields):
        # Override for SpamOverrideMixin
        return self.SPAM_CHECK_FIELDS if self.is_public and 'is_public' in saved_fields else self.SPAM_CHECK_FIELDS.intersection(
            saved_fields)

    def callback(self, callback, recursive=False, *args, **kwargs):
        """Invoke callbacks of attached add-ons and collect messages.

        :param str callback: Name of callback method to invoke
        :param bool recursive: Apply callback recursively over nodes
        :return list: List of callback messages
        """
        messages = []

        for addon in self.get_addons():
            method = getattr(addon, callback)
            message = method(self, *args, **kwargs)
            if message:
                messages.append(message)

        if recursive:
            for child in self._nodes.filter(is_deleted=False):
                messages.extend(
                    child.callback(
                        callback, recursive, *args, **kwargs
                    )
                )

        return messages

    def can_comment(self, auth):
        if self.comment_level == 'public':
            return auth.logged_in and (
                self.is_public or
                (auth.user and self.has_permission(auth.user, READ))
            )
        return self.is_contributor_or_group_member(auth.user)

    def set_node_license(self, license_detail, auth, save=False):

        license_record, license_changed = set_license(self, license_detail, auth)

        if license_changed:
            self.add_log(
                action=NodeLog.CHANGED_LICENSE,
                params={
                    'parent_node': self.parent_id,
                    'node': self._primary_key,
                    'new_license': license_record.node_license.name
                },
                auth=auth,
                save=False,
            )
            self.update_or_enqueue_on_node_updated(auth.user._id, first_save=False, saved_fields={'node_license'})

        if save:
            self.save()

    def set_privacy(self, permissions, auth=None, log=True, save=True, meeting_creation=False, check_addons=True):
        """Set the permissions for this node. Also, based on meeting_creation, queues
        an email to user about abilities of public projects.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        :param bool meeting_creation: Whether this was created due to a meetings email.
        :param bool check_addons: Check and collect messages for addons?
        """
        if auth and not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Must be an admin to change privacy settings.')
        if permissions == 'public' and not self.is_public:
            if self.is_spam or (settings.SPAM_FLAGGED_MAKE_NODE_PRIVATE and self.is_spammy):
                # TODO: Should say will review within a certain agreed upon time period.
                raise NodeStateError('This project has been marked as spam. Please contact the help desk if you think this is in error.')
            if self.is_registration:
                if self.is_pending_embargo:
                    raise NodeStateError('A registration with an unapproved embargo cannot be made public.')
                elif self.is_pending_registration:
                    raise NodeStateError('An unapproved registration cannot be made public.')
                elif self.is_pending_embargo:
                    raise NodeStateError('An unapproved embargoed registration cannot be made public.')
                elif self.is_embargoed:
                    # Embargoed registrations can be made public early
                    self.request_embargo_termination(auth=auth)
                    return False
            self.is_public = True
            self.keenio_read_key = self.generate_keenio_read_key()
        elif permissions == 'private' and self.is_public:
            if self.is_registration and not self.is_pending_embargo:
                raise NodeStateError('Public registrations must be withdrawn, not made private.')
            else:
                self.is_public = False
                self.keenio_read_key = ''
        else:
            return False

        # After set permissions callback
        if check_addons:
            for addon in self.get_addons():
                message = addon.after_set_privacy(self, permissions)
                if message:
                    status.push_status_message(message, kind='info', trust=False)

        # Update existing identifiers
        if self.get_identifier('doi'):
            doi_status = 'unavailable' if permissions == 'private' else 'public'
            enqueue_task(update_doi_metadata_on_change.s(self._id, status=doi_status))

        if log:
            action = NodeLog.MADE_PUBLIC if permissions == 'public' else NodeLog.MADE_PRIVATE
            self.add_log(
                action=action,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                },
                auth=auth,
                save=False,
            )
        if save:
            self.save()
        if auth and permissions == 'public':
            project_signals.privacy_set_public.send(auth.user, node=self, meeting_creation=meeting_creation)
        return True

    def generate_keenio_read_key(self):
        return scoped_keys.encrypt(settings.KEEN['public']['master_key'], options={
            'filters': [{
                'property_name': 'node.id',
                'operator': 'eq',
                'property_value': str(self._id)
            }],
            'allowed_operations': [READ]
        })

    @property
    def private_links_active(self):
        return self.private_links.filter(is_deleted=False)

    @property
    def private_link_keys_active(self):
        return self.private_links.filter(is_deleted=False).values_list('key', flat=True)

    @property
    def private_link_keys_deleted(self):
        return self.private_links.filter(is_deleted=True).values_list('key', flat=True)

    def get_root(self):
        sql = """
            WITH RECURSIVE ascendants AS (
              SELECT
                parent_id,
                child_id,
                1 AS LEVEL,
                ARRAY[child_id] as cids
              FROM %s
              WHERE is_node_link IS FALSE and child_id = %s
              UNION ALL
              SELECT
                S.parent_id,
                D.child_id,
                D.level + 1,
                D.cids || S.child_id
              FROM ascendants AS D
                JOIN %s AS S
                  ON D.parent_id = S.child_id
              WHERE S.is_node_link IS FALSE
                AND %s = ANY(cids)
            ) SELECT parent_id
              FROM ascendants
              WHERE child_id = %s
              ORDER BY level DESC
              LIMIT 1;
        """
        with connection.cursor() as cursor:
            node_relation_table = AsIs(NodeRelation._meta.db_table)
            cursor.execute(sql, [node_relation_table, self.pk, node_relation_table, self.pk, self.pk])
            res = cursor.fetchone()
            if res:
                return AbstractNode.objects.get(pk=res[0])
            return self

    def find_readable_antecedent(self, auth):
        """ Returns first antecendant node readable by <user>.
        """
        next_parent = self.parent_node
        while next_parent:
            if next_parent.can_view(auth):
                return next_parent
            next_parent = next_parent.parent_node

    def copy_contributors_from(self, node):
        """Copies the contibutors from node (including permissions and visibility) into this node."""
        contribs = []
        for contrib in node.contributor_set.all():
            permission = contrib.permission
            contrib.id = None
            contrib.node = self
            contribs.append(contrib)
            self.add_permission(contrib.user, permission, save=True)
        Contributor.objects.bulk_create(contribs)

    def register_node(self, schema, auth, data, parent=None, child_ids=None, provider=None):
        """Make a frozen copy of a node.

        :param schema: Schema object
        :param auth: All the auth information including user, API key.
        :param data: Form data
        :param parent Node: parent registration of registration to be created
        :param provider RegistrationProvider: provider to submit the registration to
        """
        # NOTE: Admins can register child nodes even if they don't have write access to them, but not if they are group admins
        not_contributor_or_admin_parent = not self.is_contributor(auth.user) and not self.is_admin_parent(user=auth.user, include_group_admin=False)
        cannot_edit_or_admin_parent = not self.can_edit(auth=auth) and not self.is_admin_parent(user=auth.user)
        if cannot_edit_or_admin_parent or not_contributor_or_admin_parent:
            raise PermissionsError(
                'User {} does not have permission '
                'to register this node'.format(auth.user._id)
            )
        if self.is_collection:
            raise NodeStateError('Folders may not be registered')
        original = self

        # Note: Cloning a node will clone each WikiPage on the node and all the related WikiVersions
        # and point them towards the registration
        if original.is_deleted:
            raise NodeStateError('Cannot register deleted node.')

        if not provider:
            # Avoid circular import
            from osf.models.provider import RegistrationProvider
            provider = RegistrationProvider.load('osf')

        registered = original.clone()
        registered.recast('osf.registration')

        registered.custom_citation = ''
        registered.registered_date = timezone.now()
        registered.registered_user = auth.user
        registered.registered_from = original
        registered.provider = provider
        if not registered.registered_meta:
            registered.registered_meta = {}
        registered.registered_meta[schema._id] = data

        registered.forked_from = self.forked_from
        registered.creator = self.creator
        registered.node_license = original.license.copy() if original.license else None
        registered.wiki_private_uuids = {}

        # Need to save here in order to set many-to-many fields
        registered.save()

        registered.registered_schema.add(schema)
        registered.copy_contributors_from(self)
        registered.tags.add(*self.all_tags.values_list('pk', flat=True))
        registered.subjects.add(*self.subjects.values_list('pk', flat=True))
        registered.affiliated_institutions.add(*self.affiliated_institutions.values_list('pk', flat=True))

        # Clone each log from the original node for this registration.
        self.clone_logs(registered)

        registered.is_public = False
        registered.access_requests_enabled = False
        # Copy unclaimed records to unregistered users for parent
        registered.copy_unclaimed_records()

        if parent:
            node_relation = NodeRelation.objects.get(parent=parent.registered_from, child=original)
            NodeRelation.objects.get_or_create(_order=node_relation._order, parent=parent, child=registered)

        # After register callback
        for addon in original.get_addons():
            _, message = addon.after_register(original, registered, auth.user)
            if message:
                status.push_status_message(message, kind='info', trust=False)

        for node_relation in original.node_relations.filter(child__is_deleted=False):
            node_contained = node_relation.child

            if node_relation.is_node_link:
                NodeRelation.objects.get_or_create(
                    is_node_link=True,
                    parent=registered,
                    child=node_contained
                )
                continue
            else:
                if child_ids and node_contained._id not in child_ids:
                    if node_contained.node_relations.filter(child__is_deleted=False, child__guids___id__in=child_ids, is_node_link=False).exists():
                        # We can't skip a node with children that we have to register.
                        raise NodeStateError('The parents of all child nodes being registered must be registered.')
                    continue

                # Register child nodes
                node_contained.register_node(
                    schema=schema,
                    auth=auth,
                    data=data,
                    provider=provider,
                    parent=registered,
                    child_ids=child_ids,
                )

        registered.root = None  # Recompute root on save

        registered.save()

        if settings.ENABLE_ARCHIVER:
            registered.refresh_from_db()
            project_signals.after_create_registration.send(self, dst=registered, user=auth.user)

        return registered

    def path_above(self, auth):
        parents = self.parents
        return '/' + '/'.join([p.title if p.can_view(auth) else '-- private project --' for p in reversed(parents)])

    # TODO: Deprecate this; it duplicates much of what serialize_project already
    # does
    def serialize(self, auth=None):
        """Dictionary representation of node that is nested within a NodeLog's
        representation.
        """
        # TODO: incomplete implementation
        return {
            'id': str(self._primary_key),
            'category': self.category_display,
            'node_type': self.project_or_component,
            'url': self.url,
            # TODO: Titles shouldn't contain escaped HTML in the first place
            'title': sanitize.unescape_entities(self.title),
            'path': self.path_above(auth),
            'api_url': self.api_url,
            'is_public': self.is_public,
            'is_registration': self.is_registration,
        }

    def has_node_link_to(self, node):
        return self.node_relations.filter(child=node, is_node_link=True).exists()

    def _initiate_approval(self, user, notify_initiator_on_complete=False):
        end_date = timezone.now() + settings.REGISTRATION_APPROVAL_TIME
        self.registration_approval = RegistrationApproval.objects.create(
            initiated_by=user,
            end_date=end_date,
            notify_initiator_on_complete=notify_initiator_on_complete
        )
        self.save()  # Set foreign field reference Node.registration_approval
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            self.registration_approval.add_authorizer(admin, node=node)
        self.registration_approval.save()  # Save approval's approval_state
        return self.registration_approval

    def require_approval(self, user, notify_initiator_on_complete=False):
        if not self.is_registration:
            raise NodeStateError('Only registrations can require registration approval')
        if not self.is_admin_contributor(user):
            raise PermissionsError('Only admins can initiate a registration approval')

        approval = self._initiate_approval(user, notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_INITIATED,
            params={
                'node': self.registered_from._id,
                'registration': self._id,
                'registration_approval_id': approval._id,
            },
            auth=Auth(user),
            save=True,
        )

    def get_primary(self, node):
        return NodeRelation.objects.filter(parent=self, child=node, is_node_link=False).exists()

    # TODO optimize me
    def get_descendants_recursive(self, primary_only=False):
        query = self.nodes_primary if primary_only else self._nodes
        for node in query.all():
            yield node
            if not primary_only:
                primary = self.get_primary(node)
                if primary:
                    for descendant in node.get_descendants_recursive(primary_only=primary_only):
                        yield descendant
            else:
                for descendant in node.get_descendants_recursive(primary_only=primary_only):
                    yield descendant

    @property
    def nodes_primary(self):
        """For v1 compat."""
        child_pks = NodeRelation.objects.filter(
            parent=self,
            is_node_link=False
        ).values_list('child', flat=True)
        return self._nodes.filter(pk__in=child_pks)

    @property
    def has_pointers_recursive(self):
        """Recursively checks whether the current node or any of its nodes
        contains a pointer.
        """
        if self.linked_nodes.exists():
            return True
        for node in self.nodes_primary:
            if node.has_pointers_recursive:
                return True
        return False

    def add_affiliations(self, user, new):
        # add all of the user's affiliations to the forked or templated node
        for affiliation in user.affiliated_institutions.all():
            new.affiliated_institutions.add(affiliation)

    # TODO: Optimize me (e.g. use bulk create)
    def fork_node(self, auth, title=None, parent=None):
        """Recursively fork a node.

        :param Auth auth: Consolidated authorization
        :param str title: Optional text to prepend to forked title
        :param Node parent: Sets parent, should only be non-null when recursing
        :return: Forked node
        """
        Registration = apps.get_model('osf.Registration')
        PREFIX = 'Fork of '
        user = auth.user

        # Non-contributors can't fork private nodes
        if not (self.is_public or self.has_permission(user, READ)):
            raise PermissionsError('{0!r} does not have permission to fork node {1!r}'.format(user, self._id))

        when = timezone.now()

        original = self

        if original.is_deleted:
            raise NodeStateError('Cannot fork deleted node.')

        # Note: Cloning a node will clone each WikiPage on the node and all the related WikiVersions
        # and point them towards the fork
        forked = original.clone()
        if isinstance(forked, Registration):
            forked.recast('osf.node')

        forked.custom_citation = ''
        forked.is_fork = True
        forked.forked_date = when
        forked.forked_from = original
        forked.creator = user
        forked.node_license = original.license.copy() if original.license else None
        forked.wiki_private_uuids = {}

        # Forks default to private status
        forked.is_public = False

        # Need to save here in order to access m2m fields
        forked.save()

        forked.tags.add(*self.all_tags.values_list('pk', flat=True))
        forked.subjects.add(*self.subjects.values_list('pk', flat=True))

        if parent:
            node_relation = NodeRelation.objects.get(parent=parent.forked_from, child=original)
            NodeRelation.objects.get_or_create(_order=node_relation._order, parent=parent, child=forked)

        for node_relation in original.node_relations.filter(child__is_deleted=False):
            node_contained = node_relation.child
            # Fork child nodes
            if not node_relation.is_node_link:
                try:  # Catch the potential PermissionsError above
                    node_contained.fork_node(
                        auth=auth,
                        title='',
                        parent=forked,
                    )
                except PermissionsError:
                    pass  # If this exception is thrown omit the node from the result set
            else:
                # Copy linked nodes
                NodeRelation.objects.get_or_create(
                    is_node_link=True,
                    parent=forked,
                    child=node_contained
                )

        if title is None:
            forked.title = PREFIX + original.title
        elif title == '':
            forked.title = original.title
        else:
            forked.title = title

        if len(forked.title) > 512:
            forked.title = forked.title[:512]

        self.add_affiliations(user, forked)
        forked.add_contributor(
            contributor=user,
            permissions=CREATOR_PERMISSIONS,
            log=False,
            save=False
        )

        forked.root = None  # Recompute root on save

        forked.add_log(
            action=NodeLog.NODE_FORKED,
            params={
                'parent_node': original.parent_id,
                'node': original._primary_key,
                'registration': forked._primary_key,  # TODO: Remove this in favor of 'fork'
                'fork': forked._primary_key,
            },
            auth=auth,
            log_date=when,
            save=False,
        )

        # Clone each log from the original node for this fork.
        self.clone_logs(forked)

        # After fork callback
        for addon in original.get_addons():
            addon.after_fork(original, forked, user)

        forked.save()

        # Need to call this after save for the notifications to be created with the _primary_key
        project_signals.contributor_added.send(forked, contributor=user, auth=auth, email_template='false')

        return forked

    def clone_logs(self, node, page_size=100):
        paginator = Paginator(self.logs.order_by('pk').all(), page_size)
        for page_num in paginator.page_range:
            page = paginator.page(page_num)
            # Instantiate NodeLogs "manually"
            # because BaseModel#clone() is too slow for large projects
            logs_to_create = [
                NodeLog(
                    _id=bson.ObjectId(),
                    action=log.action,
                    date=log.date,
                    params=log.params,
                    should_hide=log.should_hide,
                    foreign_user=log.foreign_user,
                    # Set foreign keys, not their objects
                    # to speed things up
                    node_id=node.pk,
                    user_id=log.user_id,
                    original_node_id=log.original_node_id
                )
                for log in page
            ]
            NodeLog.objects.bulk_create(logs_to_create)

    def use_as_template(self, auth, changes=None, top_level=True, parent=None):
        """Create a new project, using an existing project as a template.

        :param auth: The user to be assigned as creator
        :param changes: A dictionary of changes, keyed by node id, which
                        override the attributes of the template project or its
                        children.
        :param Bool top_level: indicates existence of parent TODO: deprecate
        :param Node parent: parent template. Should only be passed in during recursion
        :return: The `Node` instance created.
        """
        Registration = apps.get_model('osf.Registration')
        changes = changes or dict()

        # build the dict of attributes to change for the new node
        try:
            attributes = changes[self._id]
            # TODO: explicitly define attributes which may be changed.
        except (AttributeError, KeyError):
            attributes = dict()

        if self.is_deleted:
            raise NodeStateError('Cannot use deleted node as template.')

        # Non-contributors can't template private nodes
        if not (self.is_public or self.has_permission(auth.user, READ)):
            raise PermissionsError('{0!r} does not have permission to template node {1!r}'.format(auth.user, self._id))

        new = self.clone()
        if isinstance(new, Registration):
            new.recast('osf.node')

        new._is_templated_clone = True  # This attribute may be read in post_save handlers

        # Clear quasi-foreign fields
        new.wiki_private_uuids.clear()
        new.file_guid_to_share_uuids.clear()

        # set attributes which may be overridden by `changes`
        new.is_public = False
        new.description = ''
        new.custom_citation = ''

        # apply `changes`
        for attr, val in attributes.items():
            setattr(new, attr, val)

        # set attributes which may NOT be overridden by `changes`
        new.creator = auth.user
        new.template_node = self
        # Need to save in order to access contributors m2m table
        new.save(suppress_log=True)
        new.add_contributor(contributor=auth.user, permissions=CREATOR_PERMISSIONS, log=False, save=False)
        new.is_fork = False
        new.node_license = self.license.copy() if self.license else None

        self.add_affiliations(auth.user, new)

        # If that title hasn't been changed, apply the default prefix (once)
        if (
            new.title == self.title and top_level and
            language.TEMPLATED_FROM_PREFIX not in new.title
        ):
            new.title = ''.join((language.TEMPLATED_FROM_PREFIX, new.title,))

        if len(new.title) > 512:
            new.title = new.title[:512]

        # Slight hack - created is a read-only field.
        new.created = timezone.now()

        new.save(suppress_log=True)

        # Need to call this after save for the notifications to be created with the _primary_key
        project_signals.contributor_added.send(new, contributor=auth.user, auth=auth, email_template='false')

        # Log the creation
        new.add_log(
            NodeLog.CREATED_FROM,
            params={
                'node': new._primary_key,
                'template_node': {
                    'id': self._primary_key,
                    'url': self.url,
                    'title': self.title,
                },
            },
            auth=auth,
            log_date=new.created,
            save=False,
        )
        new.save()

        if parent:
            node_relation = NodeRelation.objects.get(parent=parent.template_node, child=self)
            NodeRelation.objects.get_or_create(_order=node_relation._order, parent=parent, child=new)

        # deal with the children of the node, if any
        for node_relation in self.node_relations.select_related('child').filter(child__is_deleted=False):
            node_contained = node_relation.child
            # template child nodes
            if not node_relation.is_node_link:
                try:  # Catch the potential PermissionsError above
                    node_contained.use_as_template(auth, changes, top_level=False, parent=new)
                except PermissionsError:
                    pass

        new.root = None
        new.save()  # Recompute root on save()
        return new

    def next_descendants(self, auth, condition=lambda auth, node: True):
        """
        Recursively find the first set of descedants under a given node that meet a given condition

        returns a list of [(node, [children]), ...]
        """
        ret = []
        for node in self._nodes.order_by('created').all():
            if condition(auth, node):
                # base case
                ret.append((node, []))
            else:
                ret.append((node, node.next_descendants(auth, condition)))
        ret = [item for item in ret if item[1] or condition(auth, item[0])]  # prune empty branches
        return ret

    def node_and_primary_descendants(self):
        """Return an iterator for a node and all of its primary (non-pointer) descendants.

        :param node Node: target Node
        """
        return itertools.chain([self], self.get_descendants_recursive(primary_only=True))

    def get_active_contributors_recursive(self, unique_users=False, *args, **kwargs):
        """Yield (admin, node) tuples for this node and
        descendant nodes. Excludes contributors on node links and inactive users.

        :param bool unique_users: If True, a given admin will only be yielded once
            during iteration.
        """
        visited_user_ids = []
        for node in self.node_and_primary_descendants(*args, **kwargs):
            for contrib in node.active_contributors(*args, **kwargs):
                if unique_users:
                    if contrib._id not in visited_user_ids:
                        visited_user_ids.append(contrib._id)
                        yield (contrib, node)
                else:
                    yield (contrib, node)

    def get_admin_contributors_recursive(self, unique_users=False, *args, **kwargs):
        """Yield (admin, node) tuples for this node and
        descendant nodes. Excludes contributors on node links and inactive users.
        Excludes group members.

        :param bool unique_users: If True, a given admin will only be yielded once
            during iteration.
        """
        visited_user_ids = []
        for node in self.node_and_primary_descendants(*args, **kwargs):
            for contrib in node.contributors.all():
                if node.has_permission(contrib, ADMIN) and contrib.is_active:
                    if unique_users:
                        if contrib._id not in visited_user_ids:
                            visited_user_ids.append(contrib._id)
                            yield (contrib, node)
                    else:
                        yield (contrib, node)

    def set_access_requests_enabled(self, access_requests_enabled, auth, save=False):
        user = auth.user
        if not self.has_permission(user, ADMIN):
            raise PermissionsError('Only admins can modify access requests enabled')
        self.access_requests_enabled = access_requests_enabled
        if self.access_requests_enabled:
            self.add_log(
                NodeLog.NODE_ACCESS_REQUESTS_ENABLED,
                {
                    'project': self.parent_id,
                    'node': self._id,
                    'user': user._id,
                },
                auth=auth
            )
        else:
            self.add_log(
                NodeLog.NODE_ACCESS_REQUESTS_DISABLED,
                {
                    'project': self.parent_id,
                    'node': self._id,
                    'user': user._id,
                },
                auth=auth
            )
        if save:
            self.save()

    def save(self, *args, **kwargs):
        from osf.models import Registration
        first_save = not bool(self.pk)
        if 'old_subjects' in kwargs.keys():
            # TODO: send this data to SHARE
            kwargs.pop('old_subjects')
        if 'suppress_log' in kwargs.keys():
            self._suppress_log = kwargs['suppress_log']
            del kwargs['suppress_log']
        else:
            self._suppress_log = False
        saved_fields = self.get_dirty_fields(check_relationship=True) or []
        ret = super(AbstractNode, self).save(*args, **kwargs)
        if saved_fields:
            self.on_update(first_save, saved_fields)

        if 'node_license' in saved_fields:
            children = list(self.descendants.filter(node_license=None, is_public=True, is_deleted=False))
            while len(children):
                batch = children[:99]
                self.bulk_update_search(batch)
                children = children[99:]

        if first_save:
            self.update_group_permissions()
            if not isinstance(self, Registration):
                Contributor.objects.get_or_create(
                    user=self.creator,
                    node=self,
                    visible=True,
                )
                self.add_permission(self.creator, ADMIN)
        return ret

    def update_or_enqueue_on_node_updated(self, user_id, first_save, saved_fields):
        """
        If an earlier version of the on_node_updated task exists in the queue, update it
        with the appropriate saved_fields. Otherwise, enqueue on_node_updated.

        This ensures that on_node_updated is only queued once for a given node.
        """
        # All arguments passed as kwargs so that we can check signature.kwargs and update as necessary
        task = get_task_from_queue('website.project.tasks.on_node_updated', predicate=lambda task: task.kwargs['node_id'] == self._id)
        if task:
            # Ensure saved_fields is JSON-serializable by coercing it to a list
            task.kwargs['saved_fields'] = list(set(task.kwargs['saved_fields']).union(saved_fields))
        else:
            enqueue_task(node_tasks.on_node_updated.s(node_id=self._id, user_id=user_id, first_save=first_save, saved_fields=saved_fields))

    def update_or_enqueue_on_resource_updated(self, user_id, first_save, saved_fields):
        # Needed for ContributorMixin
        return self.update_or_enqueue_on_node_updated(user_id, first_save, saved_fields)

    def on_update(self, first_save, saved_fields):
        User = apps.get_model('osf.OSFUser')
        request, user_id = get_request_and_user_id()
        request_headers = string_type_request_headers(request)
        self.update_or_enqueue_on_node_updated(user_id, first_save, saved_fields)

        user = User.load(user_id)
        if user and self.check_spam(user, saved_fields, request_headers):
            # Specifically call the super class save method to avoid recursion into model save method.
            super(AbstractNode, self).save()

    def resolve(self):
        """For compat with v1 Pointers."""
        return self

    def set_title(self, title, auth, save=False):
        """Set the title of this Node and log it.

        :param str title: The new title.
        :param auth: All the auth information including user, API key.
        """
        # Called so validation does not have to wait until save.
        validate_title(title)

        original_title = self.title
        new_title = sanitize.strip_html(title)
        # Title hasn't changed after sanitzation, bail out
        if original_title == new_title:
            return False
        self.title = new_title
        self.add_log(
            action=NodeLog.EDITED_TITLE,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'title_new': self.title,
                'title_original': original_title,
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def set_description(self, description, auth, save=False):
        """Set the description and log the event.

        :param str description: The new description
        :param auth: All the auth informtion including user, API key.
        :param bool save: Save self after updating.
        """
        original = self.description
        new_description = sanitize.strip_html(description)
        if original == new_description:
            return False
        self.description = new_description
        self.add_log(
            action=NodeLog.EDITED_DESCRIPTION,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'description_new': self.description,
                'description_original': original
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def set_category(self, category, auth, save=False):
        """Set the category and log the event.

        :param str category: The new category
        :param auth: All the auth informtion including user, API key.
        :param bool save: Save self after updating.
        """
        original = self.category
        new_category = category
        if original == new_category:
            return False
        self.category = new_category
        self.add_log(
            action=NodeLog.CATEGORY_UPDATED,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'category_new': self.category,
                'category_original': original
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def set_article_doi(self, article_doi, auth, save=False):
        """Set the article_doi and log the event.

        :param str article_doi: The new article doi
        :param auth: All the auth informtion including user, API key.
        :param bool save: Save self after updating.
        """
        original = self.article_doi
        new_doi = article_doi
        if original == new_doi:
            return False
        self.article_doi = new_doi
        self.add_log(
            action=NodeLog.ARTICLE_DOI_UPDATED,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'article_doi_new': self.article_doi,
                'article_doi_original': original
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        return None

    def update(self, fields, auth=None, save=True):
        """Update the node with the given fields.

        :param dict fields: Dictionary of field_name:value pairs.
        :param Auth auth: Auth object for the user making the update.
        :param bool save: Whether to save after updating the object.
        """
        if not fields:  # Bail out early if there are no fields to update
            return False
        values = {}
        for key, value in fields.items():
            if key not in self.WRITABLE_WHITELIST:
                if self.is_registration:
                    raise NodeUpdateError(reason='Registered content cannot be updated', key=key)
                else:
                    continue
            # Title, description, and category have special methods for logging purposes
            if key == 'title':
                if not self.is_bookmark_collection or not self.is_quickfiles:
                    self.set_title(title=value, auth=auth, save=False)
                else:
                    raise NodeUpdateError(reason='Bookmark collections or QuickFilesNodes cannot be renamed.', key=key)
            elif key == 'description':
                self.set_description(description=value, auth=auth, save=False)
            elif key == 'category':
                self.set_category(category=value, auth=auth, save=False)
            elif key == 'is_public':
                self.set_privacy(
                    Node.PUBLIC if value else Node.PRIVATE,
                    auth=auth,
                    log=True,
                    save=False
                )
            elif key == 'node_license':
                self.set_node_license(
                    {
                        'id': value.get('id'),
                        'year': value.get('year'),
                        'copyrightHolders': value.get('copyrightHolders') or value.get('copyright_holders', [])
                    },
                    auth,
                    save=save
                )
            elif key == 'article_doi' and self.type == 'osf.registration':
                self.set_article_doi(article_doi=value, auth=auth, save=False)
            else:
                with warnings.catch_warnings():
                    try:
                        # This is in place because historically projects and components
                        # live on different ElasticSearch indexes, and at the time of Node.save
                        # there is no reliable way to check what the old Node.category
                        # value was. When the cateogory changes it is possible to have duplicate/dead
                        # search entries, so always delete the ES doc on categoryt change
                        # TODO: consolidate Node indexes into a single index, refactor search
                        if key == 'category':
                            self.delete_search_entry()
                        ###############
                        old_value = getattr(self, key)
                        if old_value != value:
                            values[key] = {
                                'old': old_value,
                                'new': value,
                            }
                            setattr(self, key, value)
                    except AttributeError:
                        raise NodeUpdateError(reason="Invalid value for attribute '{0}'".format(key), key=key)
                    except warnings.Warning:
                        raise NodeUpdateError(reason="Attribute '{0}' doesn't exist on the Node class".format(key), key=key)
        if save:
            updated = self.get_dirty_fields()
            self.save()
        else:
            updated = []
        for key in values:
            values[key]['new'] = getattr(self, key)
        if values:
            self.add_log(
                NodeLog.UPDATED_FIELDS,
                params={
                    'node': self._id,
                    'updated_fields': {
                        key: {
                            'old': values[key]['old'],
                            'new': values[key]['new']
                        }
                        for key in values
                    }
                },
                auth=auth)
        return updated

    def add_remove_node_log(self, auth, date):
        node_to_log = self.parent_node if self.parent_node else self
        log_action = NodeLog.NODE_REMOVED if self.parent_node else NodeLog.PROJECT_DELETED
        node_to_log.add_log(
            log_action,
            params={
                'project': self._primary_key,
            },
            auth=auth,
            log_date=date,
            save=True,
        )

    def remove_node(self, auth, date=None):
        """Marks a node plus every node in its hierarchy as deleted

        TODO: Call a hook on addons
        Adds a log to the parent node if applicable

        :param auth: an instance of :class:`Auth`.
        :param date: Date node was removed
        :param datetime date: `datetime.datetime` or `None`
        """
        # TODO: rename "date" param - it's shadowing a global
        hierarchy = Node.objects.get_children(self, active=True, include_root=True).filter(is_deleted=False)
        if (not auth or isinstance(auth.user, AnonymousUser)) or (
                len(hierarchy) != (Node.objects.get_nodes_for_user(auth.user, ADMIN_NODE, hierarchy)).count()):
            raise PermissionsError(
                '{0!r} does not have permission to modify this {1}, or a component in its hierarchy.'.format(auth.user, self.category or 'node')
            )

        # After delete callback
        remove_addons(auth, hierarchy)

        Comment = apps.get_model('osf.Comment')
        Comment.objects.filter(node__id__in=hierarchy).update(root_target=None)

        log_date = date or timezone.now()
        for node in hierarchy:
            # Add log to parents
            node.is_deleted = True
            node.deleted_date = date
            node.add_remove_node_log(auth=auth, date=log_date)
            project_signals.node_deleted.send(node)

        bulk_update(hierarchy, update_fields=['is_deleted', 'deleted_date'])

        if len(hierarchy.filter(is_public=True)):
            AbstractNode.bulk_update_search(hierarchy.filter(is_public=True))

        return True

    def add_addon(self, name, auth, log=True):
        ret = super(AbstractNode, self).add_addon(name, auth)
        if ret and log:
            self.add_log(
                action=NodeLog.ADDON_ADDED,
                params={
                    'project': self.parent_id,
                    'node': self._id,
                    'addon': ret.__class__._meta.app_config.full_name,
                },
                auth=auth,
                save=False,
            )
            self.save()  # TODO Required?
        return ret

    def delete_addon(self, addon_name, auth, _force=False):
        """Delete an add-on from the node.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :param bool _force: For migration testing ONLY. Do not set to True
            in the application, or else projects will be allowed to delete
            mandatory add-ons!
        :return bool: Add-on was deleted
        """
        ret = super(AbstractNode, self).delete_addon(addon_name, auth, _force)
        if ret:
            config = settings.ADDONS_AVAILABLE_DICT[addon_name]
            self.add_log(
                action=NodeLog.ADDON_REMOVED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'addon': config.full_name,
                },
                auth=auth,
                save=False,
            )
            self.save()
            # TODO: save here or outside the conditional? @mambocab
        return ret

    def has_addon_on_children(self, addon):
        """Checks if a given node has a specific addon on child nodes
            that are not registrations or deleted
        """
        if self.has_addon(addon):
            return True

        # TODO: Optimize me into one query
        for node_relation in self.node_relations.filter(is_node_link=False, child__is_deleted=False).select_related(
                'child'):
            node = node_relation.child
            if node.has_addon_on_children(addon):
                return True
        return False

    def is_derived_from(self, other, attr):
        derived_from = getattr(self, attr)
        while True:
            if derived_from is None:
                return False
            if derived_from == other:
                return True
            derived_from = getattr(derived_from, attr)

    def is_fork_of(self, other):
        return self.is_derived_from(other, 'forked_from')

    def is_registration_of(self, other):
        return self.is_derived_from(other, 'registered_from')

    def serialize_waterbutler_credentials(self, provider_name):
        return self.get_addon(provider_name).serialize_waterbutler_credentials()

    def serialize_waterbutler_settings(self, provider_name):
        return self.get_addon(provider_name).serialize_waterbutler_settings()

    def create_waterbutler_log(self, auth, action, payload):
        try:
            metadata = payload['metadata']
            node_addon = self.get_addon(payload['provider'])
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)

        if node_addon is None:
            raise HTTPError(httplib.BAD_REQUEST)

        metadata['path'] = metadata['path'].lstrip('/')

        return node_addon.create_waterbutler_log(auth, action, metadata)

    def can_view_files(self, auth=None):
        return self.can_view(auth)

    @property
    def file_read_scope(self):
        return oauth_scopes.CoreScopes.NODE_FILE_READ

    @property
    def file_write_scope(self):
        return oauth_scopes.CoreScopes.NODE_FILE_WRITE

    def get_doi_client(self):
        if settings.DATACITE_URL and settings.DATACITE_PREFIX:
            return DataCiteClient(base_url=settings.DATACITE_URL, prefix=settings.DATACITE_PREFIX)
        else:
            return None

    def update_custom_citation(self, custom_citation, auth):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can update a custom citation')

        if (custom_citation == self.custom_citation) or not (custom_citation or self.custom_citation):
            return
        elif custom_citation == '':
            log_action = NodeLog.CUSTOM_CITATION_REMOVED
        elif self.custom_citation:
            log_action = NodeLog.CUSTOM_CITATION_EDITED
        else:
            log_action = NodeLog.CUSTOM_CITATION_ADDED

        self.custom_citation = custom_citation
        self.add_log(
            log_action,
            params={
                'node': self._primary_key,
            },
            auth=auth,
            log_date=timezone.now(),
        )
        self.save()

    @property
    def storage_usage(self):
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=self._id)

        storage_usage_total = storage_usage_cache.get(key)
        if storage_usage_total:
            return storage_usage_total
        else:
            update_storage_usage(self)  # sets cache
            return storage_usage_cache.get(key)


class NodeUserObjectPermission(UserObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - User models - we typically add object
    perms directly to Django groups instead of users, so this will be used infrequently
    """
    content_object = models.ForeignKey(AbstractNode, on_delete=models.CASCADE)


class NodeGroupObjectPermission(GroupObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - Group models. Makes permission checks faster.

    This table gives a Django group a particular permission to an AbstractNode.
    For example, every time a node is created, an admin, write, and read Django group
    are created for the node. The "write" group has write/read perms to the node.

    Those links are stored here:  content_object_id (node_id), group_id, permission_id
    """
    content_object = models.ForeignKey(AbstractNode, on_delete=models.CASCADE)


class Node(AbstractNode):
    """
    Concrete Node class: Instance of AbstractNode(TypedModel). All things that inherit
    from AbstractNode will appear in the same table and will be differentiated by the `type` column.

    FYI: Behaviors common between Registration and Node should be on the parent class.
    """

    @property
    def api_v2_url(self):
        return reverse('nodes:node-detail', kwargs={'node_id': self._id, 'version': 'v2'})

    @property
    def is_bookmark_collection(self):
        """For v1 compat"""
        return False

def remove_addons(auth, resource_object_list):
    for config in AbstractNode.ADDONS_AVAILABLE:
        try:
            settings_model = config.node_settings
        except LookupError:
            settings_model = None

        if settings_model:
            addon_list = settings_model.objects.filter(owner__in=resource_object_list, deleted=False)
            for addon in addon_list:
                addon.after_delete(auth.user)


@receiver(post_save, sender=Node)
def add_project_created_log(sender, instance, created, **kwargs):
    if created and instance.is_original and not instance._suppress_log:
        # Define log fields for non-component project
        log_action = NodeLog.PROJECT_CREATED
        log_params = {
            'node': instance._id,
        }
        if getattr(instance, 'parent_node', None):
            log_params.update({'parent_node': instance.parent_node._id})

        # Add log with appropriate fields
        instance.add_log(
            log_action,
            params=log_params,
            auth=Auth(user=instance.creator),
            log_date=instance.created,
            save=True,
        )


@receiver(post_save, sender=Node)
def send_osf_signal(sender, instance, created, **kwargs):
    if created and instance.is_original and not instance._suppress_log:
        project_signals.project_created.send(instance)


@receiver(post_save, sender=Node)
def add_default_node_addons(sender, instance, created, **kwargs):
    if (created or instance._is_templated_clone) and instance.is_original and not instance._suppress_log:
        for addon in settings.ADDONS_AVAILABLE:
            if 'node' in addon.added_default:
                instance.add_addon(addon.short_name, auth=None, log=False)

@receiver(post_save, sender=Node)
@receiver(post_save, sender='osf.Registration')
@receiver(post_save, sender='osf.QuickFilesNode')
def set_parent_and_root(sender, instance, created, *args, **kwargs):
    if getattr(instance, '_parent', None):
        NodeRelation.objects.get_or_create(
            parent=instance._parent,
            child=instance,
            is_node_link=False
        )
        # remove cached copy of parent_node
        try:
            del instance.__dict__['parent_node']
        except KeyError:
            pass
    if not instance.root:
        instance.root = instance.get_root()
        instance.save()
