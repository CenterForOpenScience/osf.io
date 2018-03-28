import functools
import itertools
import logging
import re
import urlparse
import warnings

import bson
from django.db.models import Q
from dirtyfields import DirtyFieldsMixin
from django.apps import apps
from django.contrib.contenttypes.fields import GenericRelation
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models, transaction, connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from keen import scoped_keys
from psycopg2._psycopg import AsIs
from typedmodels.models import TypedModel, TypedModelManager
from include import IncludeManager

from framework import status
from framework.celery_tasks.handlers import enqueue_task
from framework.exceptions import PermissionsError
from framework.sentry import log_exception
from addons.wiki.utils import to_mongo_key
from osf.exceptions import ValidationValueError
from osf.models.contributor import (Contributor, RecentlyAddedContributor,
                                    get_contributor_permissions)
from osf.models.identifiers import Identifier, IdentifierMixin
from osf.models.licenses import NodeLicenseRecord
from osf.models.mixins import (AddonModelMixin, CommentableMixin, Loggable,
                               NodeLinkMixin, Taggable, TaxonomizableMixin)
from osf.models.node_relation import NodeRelation
from osf.models.nodelog import NodeLog
from osf.models.sanctions import RegistrationApproval
from osf.models.private_link import PrivateLink
from osf.models.spam import SpamMixin
from osf.models.tag import Tag
from osf.models.user import OSFUser
from osf.models.validators import validate_doi, validate_title
from framework.auth.core import Auth, get_user
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.requests import DummyRequest, get_request_and_user_id
from osf.utils import sanitize
from osf.utils.workflows import DefaultStates
from website import language, settings
from website.citations.utils import datetime_to_csl
from website.exceptions import (InvalidTagError, NodeStateError,
                                TagNotFoundError, UserNotAffiliatedError)
from website.project.licenses import set_license
from website.mails import mails
from website.project import signals as project_signals
from website.project import tasks as node_tasks
from website.project.model import NodeUpdateError
from website.identifiers.tasks import update_ezid_metadata_on_change
from osf.utils.requests import get_headers_from_request
from osf.utils.permissions import (ADMIN, CREATOR_PERMISSIONS,
                                      DEFAULT_CONTRIBUTOR_PERMISSIONS, READ,
                                      WRITE, expand_permissions,
                                      reduce_permissions)
from website.util import api_url_for, api_v2_url, web_url_for
from .base import BaseModel, Guid, GuidMixin, GuidMixinQuerySet


logger = logging.getLogger(__name__)


class AbstractNodeQuerySet(GuidMixinQuerySet):

    def get_roots(self):
        return self.filter(id__in=self.exclude(type='osf.collection').exclude(type='osf.quickfilesnode').values_list('root_id', flat=True))

    def get_children(self, root, active=False):
        # If `root` is a root node, we can use the 'descendants' related name
        # rather than doing a recursive query
        if root.id == root.root_id:
            query = root.descendants.exclude(id=root.id)
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
                    return AbstractNode.objects.none()
                return AbstractNode.objects.filter(id__in=row)

    def can_view(self, user=None, private_link=None):
        qs = self.filter(is_public=True)

        if private_link is not None:
            if isinstance(private_link, PrivateLink):
                private_link = private_link.key
            if not isinstance(private_link, basestring):
                raise TypeError('"private_link" must be either {} or {}. Got {!r}'.format(str, PrivateLink, private_link))

            qs |= self.filter(private_links__is_deleted=False, private_links__key=private_link)

        if user is not None:
            if isinstance(user, OSFUser):
                user = user.pk
            if not isinstance(user, int):
                raise TypeError('"user" must be either {} or {}. Got {!r}'.format(int, OSFUser, user))

            sqs = Contributor.objects.filter(node=models.OuterRef('pk'), user__id=user, read=True)
            qs |= self.annotate(can_view=models.Exists(sqs)).filter(can_view=True)
            qs |= self.extra(where=['''
                "osf_abstractnode".id in (
                    WITH RECURSIVE implicit_read AS (
                        SELECT "osf_contributor"."node_id"
                        FROM "osf_contributor"
                        WHERE "osf_contributor"."user_id" = %s
                        AND "osf_contributor"."admin" is TRUE
                    UNION ALL
                        SELECT "osf_noderelation"."child_id"
                        FROM "implicit_read"
                        LEFT JOIN "osf_noderelation" ON "osf_noderelation"."parent_id" = "implicit_read"."node_id"
                        WHERE "osf_noderelation"."is_node_link" IS FALSE
                    ) SELECT * FROM implicit_read
                )
            '''], params=(user, ))

        return qs

class AbstractNodeManager(TypedModelManager, IncludeManager):

    def get_queryset(self):
        qs = AbstractNodeQuerySet(self.model, using=self._db)
        # Filter by typedmodels type
        return self._filter_by_type(qs)

    # AbstractNodeQuerySet methods

    def get_roots(self):
        return self.get_queryset().get_roots()

    def get_children(self, root, active=False):
        return self.get_queryset().get_children(root, active=active)

    def can_view(self, user=None, private_link=None):
        return self.get_queryset().can_view(user=user, private_link=private_link)


class AbstractNode(DirtyFieldsMixin, TypedModel, AddonModelMixin, IdentifierMixin,
                   NodeLinkMixin, CommentableMixin, SpamMixin, TaxonomizableMixin,
                   Taggable, Loggable, GuidMixin, BaseModel):
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
        'wiki_pages_current',
        'node_license',
        'preprint_file',
    }

    # Node fields that trigger a check to the spam filter on save
    SPAM_CHECK_FIELDS = {
        'title',
        'description',
        'wiki_pages_current',
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

    LICENSE_QUERY = re.sub('\s+', ' ', '''WITH RECURSIVE ascendants AS (
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
    WHERE id = (SELECT node_license_id FROM ascendants WHERE node_license_id IS NOT NULL) LIMIT 1;''')

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

    @property
    def contributors(self):
        # NOTE: _order field is generated by order_with_respect_to = 'node'
        return self._contributors.order_by('contributor___order')

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

    class Meta:
        base_manager_name = 'objects'
        index_together = (('is_public', 'is_deleted', 'type'))

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
    wiki_pages_current = DateTimeAwareJSONField(default=dict, blank=True)
    wiki_pages_versions = DateTimeAwareJSONField(default=dict, blank=True)
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DateTimeAwareJSONField(default=dict, blank=True)

    identifiers = GenericRelation(Identifier, related_query_name='nodes')

    # Preprint fields
    preprint_file = models.ForeignKey('osf.BaseFileNode',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True)
    preprint_article_doi = models.CharField(max_length=128,
                                            validators=[validate_doi],
                                            null=True, blank=True)
    _is_preprint_orphan = models.NullBooleanField(default=False)
    _has_abandoned_preprint = models.BooleanField(default=False)

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
    def is_preprint(self):
        # TODO: This is a temporary implementation.
        if not self.preprint_file_id or not self.is_public:
            return False
        if self.preprint_file.node_id == self.id:
            return self.has_submitted_preprint
        else:
            self._is_preprint_orphan = True
            return False

    @property
    def has_submitted_preprint(self):
        return self.preprints.exclude(machine_state=DefaultStates.INITIAL.value).exists()

    @property
    def is_preprint_orphan(self):
        """For v1 compat"""
        if (not self.is_preprint) and self._is_preprint_orphan:
            return True
        if self.preprint_file:
            return self.preprint_file.is_deleted
        return False

    @property
    def has_published_preprint(self):
        return self.published_preprints_queryset.exists()

    @property
    def published_preprints_queryset(self):
        return self.preprints.filter(is_published=True)

    @property
    def preprint_url(self):
        node_linked_preprint = self.linked_preprint
        if node_linked_preprint:
            return node_linked_preprint.url

    @property
    def linked_preprint(self):
        if self.is_preprint:
            try:
                # if multiple preprints per project are supported on the front end this needs to change.
                published_preprint = self.published_preprints_queryset.first()
                if published_preprint:
                    return published_preprint
                else:
                    return self.preprints.get_queryset()[0]
            except IndexError:
                pass

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
            'publisher': 'Open Science Framework',
            'type': 'webpage',
            'URL': self.display_absolute_url,
        }

        doi = self.get_identifier_value('doi')
        if doi:
            csl['DOI'] = doi

        if self.logs.exists():
            csl['issued'] = datetime_to_csl(self.logs.latest().date)

        return csl

    @classmethod
    def bulk_update_search(cls, nodes, index=None):
        from website import search
        try:
            serialize = functools.partial(search.search.update_node, index=index, bulk=True, async=False)
            search.search.bulk_update_nodes(serialize, nodes, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def update_search(self):
        from website import search

        try:
            search.search.update_node(self, bulk=False, async=True)
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
                (auth.user and self.has_permission(auth.user, 'read')) or
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
            (user and self.has_permission(user, 'write')) or is_api_node
        )

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
        if getattr(self.contributor_set.all(), '_result_cache', None):
            for contrib in self.contributor_set.all():
                if contrib.user_id == user.id:
                    return get_contributor_permissions(contrib)
        try:
            contrib = user.contributor_set.get(node=self)
        except Contributor.DoesNotExist:
            return []
        return get_contributor_permissions(contrib)

    def get_visible(self, user):
        try:
            contributor = self.contributor_set.get(user=user)
        except Contributor.DoesNotExist:
            raise ValueError(u'User {0} not in contributors'.format(user))
        return contributor.visible

    def has_permission(self, user, permission, check_parent=True):
        """Check whether user has permission.

        :param User user: User to test
        :param str permission: Required permission
        :returns: User has required permission
        """
        if not user:
            return False
        query = {'node': self, permission: True}
        has_permission = user.contributor_set.filter(**query).exists()
        if not has_permission and permission == 'read' and check_parent:
            return self.is_admin_parent(user)
        return has_permission

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

    def is_admin_parent(self, user):
        if self.has_permission(user, 'admin', check_parent=False):
            return True
        parent = self.parent_node
        if parent:
            return parent.is_admin_parent(user)
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

    @property
    def admin_contributor_ids(self):
        return self._get_admin_contributor_ids(include_self=True)

    @property
    def parent_admin_contributor_ids(self):
        return self._get_admin_contributor_ids()

    def _get_admin_contributor_ids(self, include_self=False):
        def get_admin_contributor_ids(node):
            return Contributor.objects.select_related('user').filter(
                node=node,
                user__is_active=True,
                admin=True
            ).values_list('user__guids___id', flat=True)

        contributor_ids = set(self.contributors.values_list('guids___id', flat=True))
        admin_ids = set(get_admin_contributor_ids(self)) if include_self else set()
        for parent in self.parents:
            admins = get_admin_contributor_ids(parent)
            admin_ids.update(set(admins).difference(contributor_ids))
        return admin_ids

    @property
    def admin_contributors(self):
        return OSFUser.objects.filter(
            guids___id__in=self.admin_contributor_ids
        ).order_by('family_name')

    @property
    def parent_admin_contributors(self):
        return OSFUser.objects.filter(
            guids___id__in=self.parent_admin_contributor_ids
        ).order_by('family_name')

    def set_permissions(self, user, permissions, validate=True, save=False):
        # Ensure that user's permissions cannot be lowered if they are the only admin
        if isinstance(user, Contributor):
            user = user.user

        if validate and (reduce_permissions(self.get_permissions(user)) == ADMIN and
                                 reduce_permissions(permissions) != ADMIN):
            admin_contribs = Contributor.objects.filter(node=self, admin=True)
            if admin_contribs.count() <= 1:
                raise NodeStateError('Must have at least one registered admin contributor')

        contrib_obj = Contributor.objects.get(node=self, user=user)

        for permission_level in [READ, WRITE, ADMIN]:
            if permission_level in permissions:
                setattr(contrib_obj, permission_level, True)
            else:
                setattr(contrib_obj, permission_level, False)
        contrib_obj.save()
        if save:
            self.save()

    # TODO: Remove save parameter
    def add_permission(self, user, permission, save=False):
        """Grant permission to a user.

        :param User user: User to grant permission to
        :param str permission: Permission to grant
        :param bool save: Save changes
        :raises: ValueError if user already has permission
        """
        contributor = user.contributor_set.get(node=self)
        if not getattr(contributor, permission, False):
            for perm in expand_permissions(permission):
                setattr(contributor, perm, True)
            contributor.save()
        else:
            if getattr(contributor, permission, False):
                raise ValueError('User already has permission {0}'.format(permission))
        if save:
            self.save()

    # TODO: Remove save parameter
    def remove_permission(self, user, permission, save=False):
        """Revoke permission from a user.

        :param User user: User to revoke permission from
        :param str permission: Permission to revoke
        :param bool save: Save changes
        :raises: ValueError if user does not have permission
        """
        contributor = user.contributor_set.get(node=self)
        if getattr(contributor, permission, False):
            for perm in expand_permissions(permission):
                setattr(contributor, perm, False)
            contributor.save()
        else:
            raise ValueError('User does not have permission {0}'.format(permission))
        if save:
            self.save()

    @property
    def registrations_all(self):
        """For v1 compat."""
        return self.registrations.all()

    @property
    def parent_id(self):
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
    def visible_contributors(self):
        return OSFUser.objects.filter(
            contributor__node=self,
            contributor__visible=True
        ).order_by('contributor___order')

    # visible_contributor_ids was moved to this property
    @property
    def visible_contributor_ids(self):
        return self.contributor_set.filter(visible=True) \
            .order_by('_order') \
            .values_list('user__guids___id', flat=True)

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
        return True

    def is_contributor(self, user):
        """Return whether ``user`` is a contributor on this node."""
        return user is not None and Contributor.objects.filter(user=user, node=self).exists()

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

    def add_contributor(self, contributor, permissions=None, visible=True,
                        send_email='default', auth=None, log=True, save=False):
        """Add a contributor to the project.

        :param User contributor: The contributor to be added
        :param list permissions: Permissions to grant to the contributor
        :param bool visible: Contributor is visible in project dashboard
        :param str send_email: Email preference for notifying added contributor
        :param Auth auth: All the auth information including user, API key
        :param bool log: Add log to self
        :param bool save: Save after adding contributor
        :returns: Whether contributor was added
        """
        MAX_RECENT_LENGTH = 15

        # If user is merged into another account, use master account
        contrib_to_add = contributor.merged_by if contributor.is_merged else contributor
        if contrib_to_add.is_disabled:
            raise ValidationValueError('Deactivated users cannot be added as contributors.')

        if not self.is_contributor(contrib_to_add):

            contributor_obj, created = Contributor.objects.get_or_create(user=contrib_to_add, node=self)
            contributor_obj.visible = visible

            # Add default contributor permissions
            permissions = permissions or DEFAULT_CONTRIBUTOR_PERMISSIONS
            for perm in permissions:
                setattr(contributor_obj, perm, True)
            contributor_obj.save()

            # Add contributor to recently added list for user
            if auth is not None:
                user = auth.user
                recently_added_contributor_obj, created = RecentlyAddedContributor.objects.get_or_create(
                    user=user,
                    contributor=contrib_to_add
                )
                recently_added_contributor_obj.date_added = timezone.now()
                recently_added_contributor_obj.save()
                count = user.recently_added.count()
                if count > MAX_RECENT_LENGTH:
                    difference = count - MAX_RECENT_LENGTH
                    for each in user.recentlyaddedcontributor_set.order_by('date_added')[:difference]:
                        each.delete()
            if log:
                self.add_log(
                    action=NodeLog.CONTRIB_ADDED,
                    params={
                        'project': self.parent_id,
                        'node': self._primary_key,
                        'contributors': [contrib_to_add._primary_key],
                    },
                    auth=auth,
                    save=False,
                )
            if save:
                self.save()

            if self._id:
                project_signals.contributor_added.send(self,
                                                       contributor=contributor,
                                                       auth=auth, email_template=send_email)
            self.update_search()
            self.save_node_preprints()
            return contrib_to_add, True

        # Permissions must be overridden if changed when contributor is
        # added to parent he/she is already on a child of.
        elif self.is_contributor(contrib_to_add) and permissions is not None:
            self.set_permissions(contrib_to_add, permissions)
            if save:
                self.save()

            return False
        else:
            return False

    def add_contributors(self, contributors, auth=None, log=True, save=False):
        """Add multiple contributors

        :param list contributors: A list of dictionaries of the form:
            {
                'user': <User object>,
                'permissions': <Permissions list, e.g. ['read', 'write']>,
                'visible': <Boolean indicating whether or not user is a bibliographic contributor>
            }
        :param auth: All the auth information including user, API key.
        :param log: Add log to self
        :param save: Save after adding contributor
        """
        for contrib in contributors:
            self.add_contributor(
                contributor=contrib['user'], permissions=contrib['permissions'],
                visible=contrib['visible'], auth=auth, log=False, save=False,
            )
        if log and contributors:
            self.add_log(
                action=NodeLog.CONTRIB_ADDED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'contributors': [
                        contrib['user']._id
                        for contrib in contributors
                    ],
                },
                auth=auth,
                save=False,
            )
        if save:
            self.save()

    def add_unregistered_contributor(self, fullname, email, auth, send_email='default',
                                     visible=True, permissions=None, save=False, existing_user=None):
        """Add a non-registered contributor to the project.

        :param str fullname: The full name of the person.
        :param str email: The email address of the person.
        :param Auth auth: Auth object for the user adding the contributor.
        :param User existing_user: the unregister_contributor if it is already created, otherwise None
        :returns: The added contributor
        :raises: DuplicateEmailError if user with given email is already in the database.
        """
        # Create a new user record if you weren't passed an existing user
        contributor = existing_user if existing_user else OSFUser.create_unregistered(fullname=fullname, email=email)

        contributor.add_unclaimed_record(node=self, referrer=auth.user,
                                         given_name=fullname, email=email)
        try:
            contributor.save()
        except ValidationError:  # User with same email already exists
            contributor = get_user(email=email)
            # Unregistered users may have multiple unclaimed records, so
            # only raise error if user is registered.
            if contributor.is_registered or self.is_contributor(contributor):
                raise

            contributor.add_unclaimed_record(
                node=self, referrer=auth.user, given_name=fullname, email=email
            )

            contributor.save()

        self.add_contributor(
            contributor, permissions=permissions, auth=auth,
            visible=visible, send_email=send_email, log=True, save=False
        )
        self.save()
        return contributor

    def add_contributor_registered_or_not(self, auth, user_id=None,
                                          full_name=None, email=None, send_email='false',
                                          permissions=None, bibliographic=True, index=None, save=False):

        if user_id:
            contributor = OSFUser.load(user_id)
            if not contributor:
                raise ValueError('User with id {} was not found.'.format(user_id))
            if not contributor.is_registered:
                raise ValueError(
                    'Cannot add unconfirmed user {} to node {} by guid. Add an unregistered contributor with fullname and email.'
                    .format(user_id, self._id)
                )
            if self.contributor_set.filter(user=contributor).exists():
                raise ValidationValueError('{} is already a contributor.'.format(contributor.fullname))
            contributor, _ = self.add_contributor(contributor=contributor, auth=auth, visible=bibliographic,
                                 permissions=permissions, send_email=send_email, save=True)
        else:

            try:
                contributor = self.add_unregistered_contributor(
                    fullname=full_name, email=email, auth=auth,
                    send_email=send_email, permissions=permissions,
                    visible=bibliographic, save=True
                )
            except ValidationError:
                contributor = get_user(email=email)
                if self.contributor_set.filter(user=contributor).exists():
                    raise ValidationValueError('{} is already a contributor.'.format(contributor.fullname))
                self.add_contributor(contributor=contributor, auth=auth, visible=bibliographic,
                                     send_email=send_email, permissions=permissions, save=True)

        auth.user.email_last_sent = timezone.now()
        auth.user.save()

        if index is not None:
            self.move_contributor(contributor=contributor, index=index, auth=auth, save=True)

        contributor_obj = self.contributor_set.get(user=contributor)
        contributor.permission = get_contributor_permissions(contributor_obj, as_list=False)
        contributor.bibliographic = contributor_obj.visible
        contributor.node_id = self._id
        contributor_order = list(self.get_contributor_order())
        contributor.index = contributor_order.index(contributor_obj.pk)

        if save:
            contributor.save()

        return contributor_obj

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

    def replace_contributor(self, old, new):
        try:
            contrib_obj = self.contributor_set.get(user=old)
        except Contributor.DoesNotExist:
            return False
        contrib_obj.user = new
        contrib_obj.save()

        # Remove unclaimed record for the project
        if self._id in old.unclaimed_records:
            del old.unclaimed_records[self._id]
            old.save()
        self.save_node_preprints()
        return True

    def remove_contributor(self, contributor, auth, log=True):
        """Remove a contributor from this node.

        :param contributor: User object, the contributor to be removed
        :param auth: All the auth information including user, API key.
        """

        if isinstance(contributor, Contributor):
            contributor = contributor.user

        # remove unclaimed record if necessary
        if self._primary_key in contributor.unclaimed_records:
            del contributor.unclaimed_records[self._primary_key]
            contributor.save()

        # If user is the only visible contributor, return False
        if not self.contributor_set.exclude(user=contributor).filter(visible=True).exists():
            return False

        # Node must have at least one registered admin user
        admin_query = self._get_admin_contributors_query(self._contributors.all()).exclude(user=contributor)
        if not admin_query.exists():
            return False

        contrib_obj = self.contributor_set.get(user=contributor)
        contrib_obj.delete()

        # After remove callback
        for addon in self.get_addons():
            message = addon.after_remove_contributor(self, contributor, auth)
            if message:
                # Because addons can return HTML strings, addons are responsible
                # for markupsafe-escaping any messages returned
                status.push_status_message(message, kind='info', trust=True)

        if log:
            self.add_log(
                action=NodeLog.CONTRIB_REMOVED,
                params={
                    'project': self.parent_id,
                    'node': self._id,
                    'contributors': [contributor._id],
                },
                auth=auth,
                save=False,
            )

        self.save()
        self.update_search()
        # send signal to remove this user from project subscriptions
        project_signals.contributor_removed.send(self, user=contributor)

        self.save_node_preprints()
        return True

    def remove_contributors(self, contributors, auth=None, log=True, save=False):

        results = []
        removed = []

        for contrib in contributors:
            outcome = self.remove_contributor(
                contributor=contrib, auth=auth, log=False,
            )
            results.append(outcome)
            removed.append(contrib._id)
        if log:
            self.add_log(
                action=NodeLog.CONTRIB_REMOVED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'contributors': removed,
                },
                auth=auth,
                save=False,
            )

        if save:
            self.save()

        return all(results)

    def move_contributor(self, contributor, auth, index, save=False):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can modify contributor order')
        if isinstance(contributor, OSFUser):
            contributor = self.contributor_set.get(user=contributor)
        contributor_ids = list(self.get_contributor_order())
        old_index = contributor_ids.index(contributor.id)
        contributor_ids.insert(index, contributor_ids.pop(old_index))
        self.set_contributor_order(contributor_ids)
        self.add_log(
            action=NodeLog.CONTRIB_REORDERED,
            params={
                'project': self.parent_id,
                'node': self._id,
                'contributors': [
                    contributor.user._id
                ],
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        self.save_node_preprints()

    def can_comment(self, auth):
        if self.comment_level == 'public':
            return auth.logged_in and (
                self.is_public or
                (auth.user and self.has_permission(auth.user, 'read'))
            )
        return self.is_contributor(auth.user)

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
            enqueue_task(update_ezid_metadata_on_change.s(self._id, status=doi_status))

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
            'allowed_operations': ['read']
        })

    def save_node_preprints(self):
        if self.preprint_file:
            PreprintService = apps.get_model('osf.PreprintService')
            for preprint in PreprintService.objects.filter(node_id=self.id, is_published=True):
                preprint.save()

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
            contrib.id = None
            contrib.node = self
            contribs.append(contrib)
        Contributor.objects.bulk_create(contribs)

    def register_node(self, schema, auth, data, parent=None):
        """Make a frozen copy of a node.

        :param schema: Schema object
        :param auth: All the auth information including user, API key.
        :param data: Form data
        :param parent Node: parent registration of registration to be created
        """
        # NOTE: Admins can register child nodes even if they don't have write access them
        if not self.can_edit(auth=auth) and not self.is_admin_parent(user=auth.user):
            raise PermissionsError(
                'User {} does not have permission '
                'to register this node'.format(auth.user._id)
            )
        if self.is_collection:
            raise NodeStateError('Folders may not be registered')
        original = self

        # Note: Cloning a node will clone each node wiki page version and add it to
        # `registered.wiki_pages_current` and `registered.wiki_pages_versions`.
        if original.is_deleted:
            raise NodeStateError('Cannot register deleted node.')

        registered = original.clone()
        registered.recast('osf.registration')

        registered.registered_date = timezone.now()
        registered.registered_user = auth.user
        registered.registered_from = original
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
            # Register child nodes
            if not node_relation.is_node_link:
                node_contained.register_node(
                    schema=schema,
                    auth=auth,
                    data=data,
                    parent=registered,
                )
            else:
                # Copy linked nodes
                NodeRelation.objects.get_or_create(
                    is_node_link=True,
                    parent=registered,
                    child=node_contained
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
        if not self.has_permission(user, 'admin'):
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
        if not (self.is_public or self.has_permission(user, 'read')):
            raise PermissionsError('{0!r} does not have permission to fork node {1!r}'.format(user, self._id))

        when = timezone.now()

        original = self

        if original.is_deleted:
            raise NodeStateError('Cannot fork deleted node.')

        # Note: Cloning a node will clone each node wiki page version and add it to
        # `registered.wiki_pages_current` and `registered.wiki_pages_versions`.
        forked = original.clone()
        if isinstance(forked, Registration):
            forked.recast('osf.node')

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

        if len(forked.title) > 200:
            forked.title = forked.title[:200]

        forked.add_contributor(
            contributor=user,
            permissions=CREATOR_PERMISSIONS,
            log=False,
            save=False
        )

        forked.root = None  # Recompute root on save

        forked.save()

        # Need to call this after save for the notifications to be created with the _primary_key
        project_signals.contributor_added.send(forked, contributor=user, auth=auth, email_template='false')

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
        forked.refresh_from_db()

        # After fork callback
        for addon in original.get_addons():
            addon.after_fork(original, forked, user)

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
        if not (self.is_public or self.has_permission(auth.user, 'read')):
            raise PermissionsError('{0!r} does not have permission to template node {1!r}'.format(auth.user, self._id))

        new = self.clone()
        if isinstance(new, Registration):
            new.recast('osf.node')

        new._is_templated_clone = True  # This attribute may be read in post_save handlers

        # Clear quasi-foreign fields
        new.wiki_pages_current.clear()
        new.wiki_pages_versions.clear()
        new.wiki_private_uuids.clear()
        new.file_guid_to_share_uuids.clear()

        # set attributes which may be overridden by `changes`
        new.is_public = False
        new.description = ''

        # apply `changes`
        for attr, val in attributes.iteritems():
            setattr(new, attr, val)

        # set attributes which may NOT be overridden by `changes`
        new.creator = auth.user
        new.template_node = self
        # Need to save in order to access contributors m2m table
        new.save(suppress_log=True)
        new.add_contributor(contributor=auth.user, permissions=CREATOR_PERMISSIONS, log=False, save=False)
        new.is_fork = False
        new.node_license = self.license.copy() if self.license else None

        # If that title hasn't been changed, apply the default prefix (once)
        if (
            new.title == self.title and top_level and
            language.TEMPLATED_FROM_PREFIX not in new.title
        ):
            new.title = ''.join((language.TEMPLATED_FROM_PREFIX, new.title,))

        if len(new.title) > 200:
            new.title = new.title[:200]

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

    def active_contributors(self, include=lambda n: True):
        for contrib in self.contributors.filter(is_active=True):
            if include(contrib):
                yield contrib

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

    def _get_admin_contributors_query(self, users):
        return Contributor.objects.select_related('user').filter(
            node=self,
            user__in=users,
            user__is_active=True,
            admin=True
        )

    def get_admin_contributors(self, users):
        """Return a set of all admin contributors for this node. Excludes contributors on node links and
        inactive users.
        """
        return (each.user for each in self._get_admin_contributors_query(users))

    def get_admin_contributors_recursive(self, unique_users=False, *args, **kwargs):
        """Yield (admin, node) tuples for this node and
        descendant nodes. Excludes contributors on node links and inactive users.

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

    # TODO: Optimize me
    def manage_contributors(self, user_dicts, auth, save=False):
        """Reorder and remove contributors.

        :param list user_dicts: Ordered list of contributors represented as
            dictionaries of the form:
            {'id': <id>, 'permission': <One of 'read', 'write', 'admin'>, 'visible': bool}
        :param Auth auth: Consolidated authentication information
        :param bool save: Save changes
        :raises: ValueError if any users in `users` not in contributors or if
            no admin contributors remaining
        """
        with transaction.atomic():
            users = []
            user_ids = []
            permissions_changed = {}
            visibility_removed = []
            to_retain = []
            to_remove = []
            for user_dict in user_dicts:
                user = OSFUser.load(user_dict['id'])
                if user is None:
                    raise ValueError('User not found')
                if not self.contributors.filter(id=user.id).exists():
                    raise ValueError(
                        'User {0} not in contributors'.format(user.fullname)
                    )
                permissions = expand_permissions(user_dict['permission'])
                if set(permissions) != set(self.get_permissions(user)):
                    # Validate later
                    self.set_permissions(user, permissions, validate=False, save=False)
                    permissions_changed[user._id] = permissions
                # visible must be added before removed to ensure they are validated properly
                if user_dict['visible']:
                    self.set_visible(user,
                                     visible=True,
                                     auth=auth)
                else:
                    visibility_removed.append(user)
                users.append(user)
                user_ids.append(user_dict['id'])

            for user in visibility_removed:
                self.set_visible(user,
                                 visible=False,
                                 auth=auth)

            for user in self.contributors.all():
                if user._id in user_ids:
                    to_retain.append(user)
                else:
                    to_remove.append(user)

            if users is None or not self._get_admin_contributors_query(users).exists():
                raise NodeStateError(
                    'Must have at least one registered admin contributor'
                )

            if to_retain != users:
                # Ordered Contributor PKs, sorted according to the passed list of user IDs
                sorted_contrib_ids = [
                    each.id for each in sorted(self.contributor_set.all(), key=lambda c: user_ids.index(c.user._id))
                ]
                self.set_contributor_order(sorted_contrib_ids)
                self.add_log(
                    action=NodeLog.CONTRIB_REORDERED,
                    params={
                        'project': self.parent_id,
                        'node': self._id,
                        'contributors': [
                            user._id
                            for user in users
                        ],
                    },
                    auth=auth,
                    save=False,
                )

            if to_remove:
                self.remove_contributors(to_remove, auth=auth, save=False)

            if permissions_changed:
                self.add_log(
                    action=NodeLog.PERMISSIONS_UPDATED,
                    params={
                        'project': self.parent_id,
                        'node': self._id,
                        'contributors': permissions_changed,
                    },
                    auth=auth,
                    save=False,
                )
            if save:
                self.save()

            self.save_node_preprints()

        with transaction.atomic():
            if to_remove or permissions_changed and ['read'] in permissions_changed.values():
                project_signals.write_permissions_revoked.send(self)

    # TODO: optimize me
    def update_contributor(self, user, permission, visible, auth, save=False):
        """ TODO: this method should be updated as a replacement for the main loop of
        Node#manage_contributors. Right now there are redundancies, but to avoid major
        feature creep this will not be included as this time.

        Also checks to make sure unique admin is not removing own admin privilege.
        """
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can modify contributor permissions')

        if permission:
            permissions = expand_permissions(permission)
            admins = self.contributor_set.filter(admin=True)
            if not admins.count() > 1:
                # has only one admin
                admin = admins.first()
                if admin.user == user and ADMIN not in permissions:
                    raise NodeStateError('{} is the only admin.'.format(user.fullname))
            if not self.contributor_set.filter(user=user).exists():
                raise ValueError(
                    'User {0} not in contributors'.format(user.fullname)
                )
            if set(permissions) != set(self.get_permissions(user)):
                self.set_permissions(user, permissions, save=save)
                permissions_changed = {
                    user._id: permissions
                }
                self.add_log(
                    action=NodeLog.PERMISSIONS_UPDATED,
                    params={
                        'project': self.parent_id,
                        'node': self._id,
                        'contributors': permissions_changed,
                    },
                    auth=auth,
                    save=save
                )
                with transaction.atomic():
                    if ['read'] in permissions_changed.values():
                        project_signals.write_permissions_revoked.send(self)
        if visible is not None:
            self.set_visible(user, visible, auth=auth)
            self.save_node_preprints()

    def save(self, *args, **kwargs):
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

        return ret

    def on_update(self, first_save, saved_fields):
        User = apps.get_model('osf.OSFUser')
        request, user_id = get_request_and_user_id()
        request_headers = {}
        if not isinstance(request, DummyRequest):
            request_headers = {
                k: v
                for k, v in get_headers_from_request(request).items()
                if isinstance(v, basestring)
            }
        enqueue_task(node_tasks.on_node_updated.s(self._id, user_id, first_save, saved_fields, request_headers))

        if self.preprint_file:
            # avoid circular imports
            from website.preprints.tasks import on_preprint_updated
            PreprintService = apps.get_model('osf.PreprintService')
            # .preprints wouldn't return a single deleted preprint
            for preprint in PreprintService.objects.filter(node_id=self.id, is_published=True):
                enqueue_task(on_preprint_updated.s(preprint._id))

        user = User.load(user_id)
        if user and self.check_spam(user, saved_fields, request_headers):
            # Specifically call the super class save method to avoid recursion into model save method.
            super(AbstractNode, self).save()

    def _get_spam_content(self, saved_fields):
        NodeWikiPage = apps.get_model('addons_wiki.NodeWikiPage')
        spam_fields = self.SPAM_CHECK_FIELDS if self.is_public and 'is_public' in saved_fields else self.SPAM_CHECK_FIELDS.intersection(
            saved_fields)
        content = []
        for field in spam_fields:
            if field == 'wiki_pages_current':
                newest_wiki_page = None
                for wiki_page_id in self.wiki_pages_current.values():
                    wiki_page = NodeWikiPage.load(wiki_page_id)
                    if not newest_wiki_page:
                        newest_wiki_page = wiki_page
                    elif wiki_page.date > newest_wiki_page.date:
                        newest_wiki_page = wiki_page
                if newest_wiki_page:
                    content.append(newest_wiki_page.raw_text(self).encode('utf-8'))
            else:
                content.append((getattr(self, field, None) or '').encode('utf-8'))
        if not content:
            return None
        return ' '.join(content)

    def check_spam(self, user, saved_fields, request_headers):
        if not settings.SPAM_CHECK_ENABLED:
            return False
        if settings.SPAM_CHECK_PUBLIC_ONLY and not self.is_public:
            return False
        if 'ham_confirmed' in user.system_tags:
            return False

        content = self._get_spam_content(saved_fields)
        if not content:
            return
        is_spam = self.do_check_spam(
            user.fullname,
            user.username,
            content,
            request_headers
        )
        logger.info("Node ({}) '{}' smells like {} (tip: {})".format(
            self._id, self.title.encode('utf-8'), 'SPAM' if is_spam else 'HAM', self.spam_pro_tip
        ))
        if is_spam:
            self._check_spam_user(user)
        return is_spam

    def _check_spam_user(self, user):
        if (
            settings.SPAM_ACCOUNT_SUSPENSION_ENABLED
            and (timezone.now() - user.date_confirmed) <= settings.SPAM_ACCOUNT_SUSPENSION_THRESHOLD
        ):
            self.set_privacy('private', log=False, save=False)

            # Suspend the flagged user for spam.
            if 'spam_flagged' not in user.system_tags:
                user.add_system_tag('spam_flagged')
            if not user.is_disabled:
                user.disable_account()
                user.is_registered = False
                mails.send_mail(
                    to_addr=user.username,
                    mail=mails.SPAM_USER_BANNED,
                    user=user,
                    osf_support_email=settings.OSF_SUPPORT_EMAIL
                )
            user.save()

            # Make public nodes private from this contributor
            for node in user.contributed:
                if self._id != node._id and len(node.contributors) == 1 and node.is_public and not node.is_quickfiles:
                    node.set_privacy('private', log=False, save=True)

    def flag_spam(self):
        """ Overrides SpamMixin#flag_spam.
        """
        super(AbstractNode, self).flag_spam()
        if settings.SPAM_FLAGGED_MAKE_NODE_PRIVATE:
            self.set_privacy(Node.PRIVATE, auth=None, log=False, save=False, check_addons=False)
            log = self.add_log(
                action=NodeLog.MADE_PRIVATE,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                },
                auth=None,
                save=False
            )
            log.should_hide = True
            log.save()

    def confirm_spam(self, save=False):
        super(AbstractNode, self).confirm_spam(save=False)
        self.set_privacy(Node.PRIVATE, auth=None, log=False, save=False)
        log = self.add_log(
            action=NodeLog.MADE_PRIVATE,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
            },
            auth=None,
            save=False
        )
        log.should_hide = True
        log.save()
        if save:
            self.save()

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

    def update(self, fields, auth=None, save=True):
        """Update the node with the given fields.

        :param dict fields: Dictionary of field_name:value pairs.
        :param Auth auth: Auth object for the user making the update.
        :param bool save: Whether to save after updating the object.
        """
        if not fields:  # Bail out early if there are no fields to update
            return False
        values = {}
        for key, value in fields.iteritems():
            if key not in self.WRITABLE_WHITELIST:
                continue
            if self.is_registration and key != 'is_public':
                raise NodeUpdateError(reason='Registered content cannot be updated', key=key)
            # Title and description have special methods for logging purposes
            if key == 'title':
                if not self.is_bookmark_collection or not self.is_quickfiles:
                    self.set_title(title=value, auth=auth, save=False)
                else:
                    raise NodeUpdateError(reason='Bookmark collections or QuickFilesNodes cannot be renamed.', key=key)
            elif key == 'description':
                self.set_description(description=value, auth=auth, save=False)
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

    def remove_node(self, auth, date=None):
        """Marks a node as deleted.

        TODO: Call a hook on addons
        Adds a log to the parent node if applicable

        :param auth: an instance of :class:`Auth`.
        :param date: Date node was removed
        :type date: `datetime.datetime` or `None`
        """
        # TODO: rename "date" param - it's shadowing a global
        if not self.can_edit(auth):
            raise PermissionsError(
                '{0!r} does not have permission to modify this {1}'.format(auth.user, self.category or 'node')
            )

        if Node.objects.get_children(self, active=True):
            raise NodeStateError('Any child components must be deleted prior to deleting this project.')

        # After delete callback
        for addon in self.get_addons():
            message = addon.after_delete(self, auth.user)
            if message:
                status.push_status_message(message, kind='info', trust=False)

        log_date = date or timezone.now()

        # Add log to parent
        if self.parent_node:
            self.parent_node.add_log(
                NodeLog.NODE_REMOVED,
                params={
                    'project': self._primary_key,
                },
                auth=auth,
                log_date=log_date,
                save=True,
            )
        else:
            self.add_log(
                NodeLog.PROJECT_DELETED,
                params={
                    'project': self._primary_key,
                },
                auth=auth,
                log_date=log_date,
                save=True,
            )

        self.is_deleted = True
        self.deleted_date = date
        self.save()

        project_signals.node_deleted.send(self)

        return True

    def admin_public_wiki(self, user):
        return (
            self.has_addon('wiki') and
            self.has_permission(user, 'admin') and
            self.is_public
        )

    def admin_of_wiki(self, user):
        return (
            self.has_addon('wiki') and
            self.has_permission(user, 'admin')
        )

    def include_wiki_settings(self, user):
        """Check if node meets requirements to make publicly editable."""
        return self.get_descendants_recursive()

    def get_wiki_page(self, name=None, version=None, id=None):
        NodeWikiPage = apps.get_model('addons_wiki.NodeWikiPage')
        if name:
            name = (name or '').strip()
            key = to_mongo_key(name)
            try:
                if version and (isinstance(version, int) or version.isdigit()):
                    id = self.wiki_pages_versions[key][int(version) - 1]
                elif version == 'previous':
                    id = self.wiki_pages_versions[key][-2]
                elif version == 'current' or version is None:
                    id = self.wiki_pages_current[key]
                else:
                    return None
            except (KeyError, IndexError):
                return None
        return NodeWikiPage.load(id)

    def update_node_wiki(self, name, content, auth):
        """Update the node's wiki page with new content.

        :param page: A string, the page's name, e.g. ``"home"``.
        :param content: A string, the posted content.
        :param auth: All the auth information including user, API key.
        """
        NodeWikiPage = apps.get_model('addons_wiki.NodeWikiPage')
        Comment = apps.get_model('osf.Comment')

        name = (name or '').strip()
        key = to_mongo_key(name)
        has_comments = False
        current = None

        if key not in self.wiki_pages_current:
            if key in self.wiki_pages_versions:
                version = len(self.wiki_pages_versions[key]) + 1
            else:
                version = 1
        else:
            current = NodeWikiPage.load(self.wiki_pages_current[key])
            version = current.version + 1
            current.save()
            if Comment.objects.filter(root_target=current.guids.all()[0]).exists():
                has_comments = True

        new_page = NodeWikiPage(
            page_name=name,
            version=version,
            user=auth.user,
            node=self,
            content=content
        )
        new_page.save()

        if has_comments:
            Comment.objects.filter(root_target=current.guids.all()[0]).update(root_target=Guid.load(new_page._id))
            Comment.objects.filter(target=current.guids.all()[0]).update(target=Guid.load(new_page._id))

        if current:
            for contrib in self.contributors:
                if contrib.comments_viewed_timestamp.get(current._id, None):
                    timestamp = contrib.comments_viewed_timestamp[current._id]
                    contrib.comments_viewed_timestamp[new_page._id] = timestamp
                    del contrib.comments_viewed_timestamp[current._id]
                    contrib.save()

        # check if the wiki page already exists in versions (existed once and is now deleted)
        if key not in self.wiki_pages_versions:
            self.wiki_pages_versions[key] = []
        self.wiki_pages_versions[key].append(new_page._primary_key)
        self.wiki_pages_current[key] = new_page._primary_key

        self.add_log(
            action=NodeLog.WIKI_UPDATED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'page': new_page.page_name,
                'page_id': new_page._primary_key,
                'version': new_page.version,
            },
            auth=auth,
            log_date=new_page.date,
            save=False,
        )
        self.save()

    # TODO: Move to wiki add-on
    def rename_node_wiki(self, name, new_name, auth):
        """Rename the node's wiki page with new name.

        :param name: A string, the page's name, e.g. ``"My Page"``.
        :param new_name: A string, the new page's name, e.g. ``"My Renamed Page"``.
        :param auth: All the auth information including user, API key.

        """
        # TODO: Fix circular imports
        from addons.wiki.exceptions import (
            PageCannotRenameError,
            PageConflictError,
            PageNotFoundError,
        )

        name = (name or '').strip()
        key = to_mongo_key(name)
        new_name = (new_name or '').strip()
        new_key = to_mongo_key(new_name)
        page = self.get_wiki_page(name)

        if key == 'home':
            raise PageCannotRenameError('Cannot rename wiki home page')
        if not page:
            raise PageNotFoundError('Wiki page not found')
        if (new_key in self.wiki_pages_current and key != new_key) or new_key == 'home':
            raise PageConflictError(
                'Page already exists with name {0}'.format(
                    new_name,
                )
            )

        # rename the page first in case we hit a validation exception.
        old_name = page.page_name
        page.rename(new_name)

        # TODO: merge historical records like update (prevents log breaks)
        # transfer the old page versions/current keys to the new name.
        if key != new_key:
            self.wiki_pages_versions[new_key] = self.wiki_pages_versions[key]
            del self.wiki_pages_versions[key]
            self.wiki_pages_current[new_key] = self.wiki_pages_current[key]
            del self.wiki_pages_current[key]
            if key in self.wiki_private_uuids:
                self.wiki_private_uuids[new_key] = self.wiki_private_uuids[key]
                del self.wiki_private_uuids[key]

        self.add_log(
            action=NodeLog.WIKI_RENAMED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'page': page.page_name,
                'page_id': page._primary_key,
                'old_page': old_name,
                'version': page.version,
            },
            auth=auth,
            save=True,
        )

    def delete_node_wiki(self, name, auth):
        name = (name or '').strip()
        key = to_mongo_key(name)
        page = self.get_wiki_page(key)

        del self.wiki_pages_current[key]
        if key != 'home':
            del self.wiki_pages_versions[key]

        self.add_log(
            action=NodeLog.WIKI_DELETED,
            params={
                'project': self.parent_id,
                'node': self._primary_key,
                'page': page.page_name,
                'page_id': page._primary_key,
            },
            auth=auth,
            save=False,
        )
        self.save()

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

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            ('view_node', 'Can view node details'),
        )


##### Signal listeners #####
@receiver(post_save, sender=Node)
@receiver(post_save, sender='osf.QuickFilesNode')
def add_creator_as_contributor(sender, instance, created, **kwargs):
    if created:
        Contributor.objects.get_or_create(
            user=instance.creator,
            node=instance,
            visible=True,
            read=True,
            write=True,
            admin=True
        )


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
