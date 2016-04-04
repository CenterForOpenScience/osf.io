# -*- coding: utf-8 -*-
import itertools
import functools
import os
import re
import logging
import pymongo
import datetime
from dateutil.parser import parse as parse_date
import urlparse
from collections import OrderedDict
import warnings

import pytz
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator

from modularodm import Q
from modularodm import fields
from modularodm.validators import MaxLengthValidator
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError

from framework import status
from framework.mongo import ObjectId
from framework.mongo import StoredObject
from framework.mongo import validators
from framework.addons import AddonModelMixin
from framework.auth import get_user, User, Auth
from framework.auth import signals as auth_signals
from framework.exceptions import PermissionsError
from framework.guid.model import GuidStoredObject, Guid
from framework.auth.utils import privacy_info_handle
from framework.analytics import tasks as piwik_tasks
from framework.mongo.utils import to_mongo_key, unique_on
from framework.analytics import (
    get_basic_counters, increment_user_activity_counters
)
from framework.sentry import log_exception
from framework.transactions.context import TokuTransaction
from framework.utils import iso8601format

from website import language, mails, settings, tokens
from website.util import web_url_for
from website.util import api_url_for
from website.util import api_v2_url
from website.util import sanitize
from website.exceptions import (
    NodeStateError,
    InvalidSanctionApprovalToken, InvalidSanctionRejectionToken,
    UserNotAffiliatedError,
)
from website.institutions.model import Institution, AffiliatedInstitutionsList
from website.citations.utils import datetime_to_csl
from website.identifiers.model import IdentifierMixin
from website.util.permissions import expand_permissions
from website.util.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS, ADMIN
from website.project.commentable import Commentable
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.licenses import (
    NodeLicense,
    NodeLicenseRecord,
)
from website.project import signals as project_signals
from website.project.spam.model import SpamMixin
from website.prereg import utils as prereg_utils

logger = logging.getLogger(__name__)

VIEW_PROJECT_URL_TEMPLATE = settings.DOMAIN + '{node_id}/'

def has_anonymous_link(node, auth):
    """check if the node is anonymous to the user

    :param Node node: Node which the user wants to visit
    :param str link: any view-only link in the current url
    :return bool anonymous: Whether the node is anonymous to the user or not
    """
    if auth.private_link:
        return auth.private_link.anonymous
    return False

@unique_on(['name', 'schema_version', '_id'])
class MetaSchema(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    name = fields.StringField()
    schema = fields.DictionaryField()
    category = fields.StringField()

    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = fields.IntegerField()

    @property
    def _config(self):
        return self.schema.get('config', {})

    @property
    def requires_approval(self):
        return self._config.get('requiresApproval', False)

    @property
    def fulfills(self):
        return self._config.get('fulfills', [])

    @property
    def messages(self):
        return self._config.get('messages', {})

    @property
    def requires_consent(self):
        return self._config.get('requiresConsent', False)

def ensure_schema(schema, name, version=1):
    schema_obj = None
    try:
        schema_obj = MetaSchema.find_one(
            Q('name', 'eq', name) &
            Q('schema_version', 'eq', version)
        )
    except NoResultsFound:
        meta_schema = {
            'name': name,
            'schema_version': version,
            'schema': schema,
        }
        schema_obj = MetaSchema(**meta_schema)
    else:
        schema_obj.schema = schema
    schema_obj.save()
    return schema_obj


def ensure_schemas():
    """Import meta-data schemas from JSON to database if not already loaded
    """
    for schema in OSF_META_SCHEMAS:
        ensure_schema(schema, schema['name'], version=schema.get('version', 1))


class MetaData(GuidStoredObject):
    # TODO: This model may be unused; potential candidate for deprecation depending on contents of production database
    _id = fields.StringField(primary=True)

    target = fields.AbstractForeignField()
    data = fields.DictionaryField()

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_modified = fields.DateTimeField(auto_now=datetime.datetime.utcnow)


class Comment(GuidStoredObject, SpamMixin, Commentable):

    __guid_min_length__ = 12

    OVERVIEW = "node"
    FILES = "files"
    WIKI = 'wiki'

    _id = fields.StringField(primary=True)

    user = fields.ForeignField('user', required=True)
    # the node that the comment belongs to
    node = fields.ForeignField('node', required=True)
    # the direct 'parent' of the comment (e.g. the target of a comment reply is another comment)
    target = fields.AbstractForeignField(required=True)
    # The file or project overview page that the comment is for
    root_target = fields.AbstractForeignField()

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_modified = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow, editable=True)
    modified = fields.BooleanField(default=False)
    is_deleted = fields.BooleanField(default=False)
    # The type of root_target: node/files
    page = fields.StringField()
    content = fields.StringField(required=True,
                                 validate=[MaxLengthValidator(settings.COMMENT_MAXLENGTH), validators.string_required])
    # The mentioned users
    new_mentions = fields.ListField(fields.StringField(default=[]))
    old_mentions = fields.ListField(fields.StringField())

    # For Django compatibility
    @property
    def pk(self):
        return self._id

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/comments/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'comments'

    @property
    def root_target_page(self):
        """The page type associated with the object/Comment.root_target."""
        return None

    def belongs_to_node(self, node_id):
        """Check whether the comment is attached to the specified node."""
        return self.node._id == node_id

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_comment_page_url(self):
        if isinstance(self.root_target.referent, Node):
            return self.node.absolute_url
        return settings.DOMAIN + str(self.root_target._id) + '/'

    def get_content(self, auth):
        """ Returns the comment content if the user is allowed to see it. Deleted comments
        can only be viewed by the user who created the comment."""
        if not auth and not self.node.is_public:
            raise PermissionsError

        if self.is_deleted and ((not auth or auth.user.is_anonymous())
                                or (auth and not auth.user.is_anonymous() and self.user._id != auth.user._id)):
            return None

        return self.content

    def get_comment_page_title(self):
        if self.page == Comment.FILES:
            return self.root_target.referent.name
        elif self.page == Comment.WIKI:
            return self.root_target.referent.page_name
        return ''

    def get_comment_page_type(self):
        if self.page == Comment.FILES:
            return 'file'
        elif self.page == Comment.WIKI:
            return 'wiki'
        return self.node.project_or_component

	# TODO: check whether user is a contributor on project
    def get_mentions(self, auth):
        """ Returns the comment mentions if the user is allowed to see it. Deleted comments
        can only be viewed by the user who created the comment."""
        if not auth and not self.node.is_public:
            raise PermissionsError

        if self.is_deleted and ((not auth or auth.user.is_anonymous())
                                or (auth and not auth.user.is_anonymous() and self.user._id != auth.user._id)):
            return None

        return self.new_mentions

    @classmethod
    def find_n_unread(cls, user, node, page, root_id=None):
        if node.is_contributor(user):
            if page == Comment.OVERVIEW:
                view_timestamp = user.get_node_comment_timestamps(target_id=node._id)
                root_target = Guid.load(node._id)
            elif page == Comment.FILES or page == Comment.WIKI:
                view_timestamp = user.get_node_comment_timestamps(target_id=root_id)
                root_target = Guid.load(root_id)
            else:
                raise ValueError('Invalid page')
            return Comment.find(Q('node', 'eq', node) &
                                Q('user', 'ne', user) &
                                Q('is_deleted', 'eq', False) &
                                (Q('date_created', 'gt', view_timestamp) |
                                Q('date_modified', 'gt', view_timestamp)) &
                                Q('root_target', 'eq', root_target)).count()

        return 0

    @classmethod
    def create(cls, auth, **kwargs):
        comment = cls(**kwargs)
        if not comment.node.can_comment(auth):
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        log_dict = {
            'project': comment.node.parent_id,
            'node': comment.node._id,
            'user': comment.user._id,
            'comment': comment._id,
        }
        if isinstance(comment.target.referent, Comment):
            comment.root_target = comment.target.referent.root_target
        else:
            comment.root_target = comment.target

        page = getattr(comment.root_target.referent, 'root_target_page', None)
        if not page:
            raise ValueError('Invalid root target.')
        comment.page = page

        log_dict.update(comment.root_target.referent.get_extra_log_params(comment))

        comment.save()

        comment.node.add_log(
            NodeLog.COMMENT_ADDED,
            log_dict,
            auth=auth,
            save=False,
        )

        # check if there are mentions and then send signal
        if (comment.new_mentions):
            project_signals.mention_added.send(comment, auth=auth)
            # copy new_mentions to old_mentions
            comment.old_mentions = comment.new_mentions

        comment.node.save()
        project_signals.comment_added.send(comment, auth=auth)

        return comment

    def edit(self, content, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to edit this comment'.format(auth.user))
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.content = content
        self.modified = True
        self.date_modified = datetime.datetime.utcnow()
        if save:
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_UPDATED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()

    def delete(self, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        self.is_deleted = True
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.date_modified = datetime.datetime.utcnow()
        if save:
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_REMOVED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()

    def undelete(self, auth, save=False):
        if not self.node.can_comment(auth) or self.user._id != auth.user._id:
            raise PermissionsError('{0!r} does not have permission to comment on this node'.format(auth.user))
        self.is_deleted = False
        log_dict = {
            'project': self.node.parent_id,
            'node': self.node._id,
            'user': self.user._id,
            'comment': self._id,
        }
        log_dict.update(self.root_target.referent.get_extra_log_params(self))
        self.date_modified = datetime.datetime.utcnow()
        if save:
            self.save()
            self.node.add_log(
                NodeLog.COMMENT_RESTORED,
                log_dict,
                auth=auth,
                save=False,
            )
            self.node.save()


@unique_on(['params.node', '_id'])
class NodeLog(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    __indices__ = [{
        'key_or_list': [
            ('user', 1),
            ('node', 1)
        ],
    }, {
        'key_or_list': [
            ('node', 1),
            ('should_hide', 1),
            ('date', -1)
        ]
    }]

    date = fields.DateTimeField(default=datetime.datetime.utcnow, index=True)
    action = fields.StringField(index=True)
    params = fields.DictionaryField()
    should_hide = fields.BooleanField(default=False)
    original_node = fields.ForeignField('node', index=True)
    node = fields.ForeignField('node', index=True)

    was_connected_to = fields.ForeignField('node', list=True)

    user = fields.ForeignField('user', index=True)
    foreign_user = fields.StringField()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants -- NOTE: templates stored in log_templates.mako
    CREATED_FROM = 'created_from'

    PROJECT_CREATED = 'project_created'
    PROJECT_REGISTERED = 'project_registered'
    PROJECT_DELETED = 'project_deleted'

    NODE_CREATED = 'node_created'
    NODE_FORKED = 'node_forked'
    NODE_REMOVED = 'node_removed'

    POINTER_CREATED = 'pointer_created'
    POINTER_FORKED = 'pointer_forked'
    POINTER_REMOVED = 'pointer_removed'

    WIKI_UPDATED = 'wiki_updated'
    WIKI_DELETED = 'wiki_deleted'
    WIKI_RENAMED = 'wiki_renamed'

    MADE_WIKI_PUBLIC = 'made_wiki_public'
    MADE_WIKI_PRIVATE = 'made_wiki_private'

    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    CONTRIB_REORDERED = 'contributors_reordered'

    CHECKED_IN = 'checked_in'
    CHECKED_OUT = 'checked_out'

    PERMISSIONS_UPDATED = 'permissions_updated'

    MADE_PRIVATE = 'made_private'
    MADE_PUBLIC = 'made_public'

    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'

    FILE_TAG_ADDED = 'file_tag_added'
    FILE_TAG_REMOVED = 'file_tag_removed'

    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'
    CHANGED_LICENSE = 'license_changed'

    UPDATED_FIELDS = 'updated_fields'

    FILE_MOVED = 'addon_file_moved'
    FILE_COPIED = 'addon_file_copied'
    FILE_RENAMED = 'addon_file_renamed'

    FOLDER_CREATED = 'folder_created'

    FILE_ADDED = 'file_added'
    FILE_UPDATED = 'file_updated'
    FILE_REMOVED = 'file_removed'
    FILE_RESTORED = 'file_restored'

    ADDON_ADDED = 'addon_added'
    ADDON_REMOVED = 'addon_removed'
    COMMENT_ADDED = 'comment_added'
    COMMENT_REMOVED = 'comment_removed'
    COMMENT_UPDATED = 'comment_updated'
    COMMENT_RESTORED = 'comment_restored'

    CITATION_ADDED = 'citation_added'
    CITATION_EDITED = 'citation_edited'
    CITATION_REMOVED = 'citation_removed'

    MADE_CONTRIBUTOR_VISIBLE = 'made_contributor_visible'
    MADE_CONTRIBUTOR_INVISIBLE = 'made_contributor_invisible'

    EXTERNAL_IDS_ADDED = 'external_ids_added'

    EMBARGO_APPROVED = 'embargo_approved'
    EMBARGO_CANCELLED = 'embargo_cancelled'
    EMBARGO_COMPLETED = 'embargo_completed'
    EMBARGO_INITIATED = 'embargo_initiated'
    RETRACTION_APPROVED = 'retraction_approved'
    RETRACTION_CANCELLED = 'retraction_cancelled'
    RETRACTION_INITIATED = 'retraction_initiated'

    REGISTRATION_APPROVAL_CANCELLED = 'registration_cancelled'
    REGISTRATION_APPROVAL_INITIATED = 'registration_initiated'
    REGISTRATION_APPROVAL_APPROVED = 'registration_approved'

    PRIMARY_INSTITUTION_CHANGED = 'primary_institution_changed'
    PRIMARY_INSTITUTION_REMOVED = 'primary_institution_removed'

    actions = [CHECKED_IN, CHECKED_OUT, FILE_TAG_REMOVED, FILE_TAG_ADDED, CREATED_FROM, PROJECT_CREATED, PROJECT_REGISTERED, PROJECT_DELETED, NODE_CREATED, NODE_FORKED, NODE_REMOVED, POINTER_CREATED, POINTER_FORKED, POINTER_REMOVED, WIKI_UPDATED, WIKI_DELETED, WIKI_RENAMED, MADE_WIKI_PUBLIC, MADE_WIKI_PRIVATE, CONTRIB_ADDED, CONTRIB_REMOVED, CONTRIB_REORDERED, PERMISSIONS_UPDATED, MADE_PRIVATE, MADE_PUBLIC, TAG_ADDED, TAG_REMOVED, EDITED_TITLE, EDITED_DESCRIPTION, UPDATED_FIELDS, FILE_MOVED, FILE_COPIED, FOLDER_CREATED, FILE_ADDED, FILE_UPDATED, FILE_REMOVED, FILE_RESTORED, ADDON_ADDED, ADDON_REMOVED, COMMENT_ADDED, COMMENT_REMOVED, COMMENT_UPDATED, MADE_CONTRIBUTOR_VISIBLE, MADE_CONTRIBUTOR_INVISIBLE, EXTERNAL_IDS_ADDED, EMBARGO_APPROVED, EMBARGO_CANCELLED, EMBARGO_COMPLETED, EMBARGO_INITIATED, RETRACTION_APPROVED, RETRACTION_CANCELLED, RETRACTION_INITIATED, REGISTRATION_APPROVAL_CANCELLED, REGISTRATION_APPROVAL_INITIATED, REGISTRATION_APPROVAL_APPROVED, CITATION_ADDED, CITATION_EDITED, CITATION_REMOVED, PRIMARY_INSTITUTION_CHANGED, PRIMARY_INSTITUTION_REMOVED]

    def __repr__(self):
        return ('<NodeLog({self.action!r}, params={self.params!r}) '
                'with id {self._id!r}>').format(self=self)

    # For Django compatibility
    @property
    def pk(self):
        return self._id

    def clone_node_log(self, node_id):
        """
        When a node is forked or registered, all logs on the node need to be cloned for the fork or registration.
        :param node_id:
        :return: cloned log
        """
        original_log = self.load(self._id)
        node = Node.find(Q('_id', 'eq', node_id))[0]
        log_clone = original_log.clone()
        log_clone.node = node
        log_clone.original_node = original_log.original_node
        log_clone.user = original_log.user
        log_clone.save()
        return log_clone

    @property
    def tz_date(self):
        '''Return the timezone-aware date.
        '''
        # Date should always be defined, but a few logs in production are
        # missing dates; return None and log error if date missing
        if self.date:
            return self.date.replace(tzinfo=pytz.UTC)
        logger.error('Date missing on NodeLog {}'.format(self._primary_key))

    @property
    def formatted_date(self):
        '''Return the timezone-aware, ISO-formatted string representation of
        this log's date.
        '''
        if self.tz_date:
            return self.tz_date.isoformat()

    def can_view(self, node, auth):
        return node.can_view(auth)

    def _render_log_contributor(self, contributor, anonymous=False):
        user = User.load(contributor)
        if not user:
            # Handle legacy non-registered users, which were
            # represented as a dict
            if isinstance(contributor, dict):
                if 'nr_name' in contributor:
                    return {
                        'fullname': contributor['nr_name'],
                        'registered': False,
                    }
            return None
        if self.node:
            fullname = user.display_full_name(node=self.node)
        else:
            fullname = user.fullname
        return {
            'id': privacy_info_handle(user._primary_key, anonymous),
            'fullname': privacy_info_handle(fullname, anonymous, name=True),
            'registered': user.is_registered,
        }

    @property
    def absolute_api_v2_url(self):
        path = '/logs/{}/'.format(self._id)
        return api_v2_url(path)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_url(self):
        return self.absolute_api_v2_url


class Tag(StoredObject):

    _id = fields.StringField(primary=True, validate=MaxLengthValidator(128))
    lower = fields.StringField(index=True, validate=MaxLengthValidator(128))

    def __init__(self, _id, lower=None, **kwargs):
        super(Tag, self).__init__(_id=_id, lower=lower or _id.lower(), **kwargs)

    def __repr__(self):
        return '<Tag({self.lower!r}) with id {self._id!r}>'.format(self=self)

    @property
    def url(self):
        return '/search/?tags={}'.format(self._id)


class Pointer(StoredObject):
    """A link to a Node. The Pointer delegates all but a few methods to its
    contained Node. Forking and registration are overridden such that the
    link is cloned, but its contained Node is not.
    """
    #: Whether this is a pointer or not
    primary = False

    _id = fields.StringField()
    node = fields.ForeignField('node')

    _meta = {'optimistic': True}

    def _clone(self):
        if self.node:
            clone = self.clone()
            clone.node = self.node
            clone.save()
            return clone

    def fork_node(self, *args, **kwargs):
        return self._clone()

    def register_node(self, *args, **kwargs):
        return self._clone()

    def use_as_template(self, *args, **kwargs):
        return self._clone()

    def resolve(self):
        return self.node

    def __getattr__(self, item):
        """Delegate attribute access to the node being pointed to."""
        # Prevent backref lookups from being overriden by proxied node
        try:
            return super(Pointer, self).__getattr__(item)
        except AttributeError:
            pass
        if self.node:
            return getattr(self.node, item)
        raise AttributeError(
            'Pointer object has no attribute {0}'.format(
                item
            )
        )


def get_pointer_parent(pointer):
    """Given a `Pointer` object, return its parent node.
    """
    # The `parent_node` property of the `Pointer` schema refers to the parents
    # of the pointed-at `Node`, not the parents of the `Pointer`; use the
    # back-reference syntax to find the parents of the `Pointer`.
    parent_refs = pointer.node__parent
    assert len(parent_refs) == 1, 'Pointer must have exactly one parent.'
    return parent_refs[0]


def validate_category(value):
    """Validator for Node#category. Makes sure that the value is one of the
    categories defined in CATEGORY_MAP.
    """
    if value not in Node.CATEGORY_MAP.keys():
        raise ValidationValueError('Invalid value for category.')
    return True


def validate_title(value):
    """Validator for Node#title. Makes sure that the value exists and is not
    above 200 characters.
    """
    if value is None or not value.strip():
        raise ValidationValueError('Title cannot be blank.')

    value = sanitize.strip_html(value)

    if value is None or not value.strip():
        raise ValidationValueError('Invalid title.')

    if len(value) > 200:
        raise ValidationValueError('Title cannot exceed 200 characters.')

    return True


def validate_user(value):
    if value != {}:
        user_id = value.iterkeys().next()
        if User.find(Q('_id', 'eq', user_id)).count() != 1:
            raise ValidationValueError('User does not exist.')
    return True


class NodeUpdateError(Exception):
    def __init__(self, reason, key, *args, **kwargs):
        super(NodeUpdateError, self).__init__(*args, **kwargs)
        self.key = key
        self.reason = reason


class Node(GuidStoredObject, AddonModelMixin, IdentifierMixin, Commentable):

    #: Whether this is a pointer or not
    primary = True

    __indices__ = [
        {
            'unique': False,
            'key_or_list': [
                ('date_modified', pymongo.DESCENDING),
            ]
        },
        #  Dollar sign indexes don't actually do anything
        #  This index has been moved to scripts/indices.py#L30
        # {
        #     'unique': False,
        #     'key_or_list': [
        #         ('tags.$', pymongo.ASCENDING),
        #         ('is_public', pymongo.ASCENDING),
        #         ('is_deleted', pymongo.ASCENDING),
        #         ('institution_id', pymongo.ASCENDING),
        #     ]
        # },
        {
            'unique': False,
            'key_or_list': [
                ('is_deleted', pymongo.ASCENDING),
                ('is_collection', pymongo.ASCENDING),
                ('is_public', pymongo.ASCENDING),
                ('institution_id', pymongo.ASCENDING),
                ('is_registration', pymongo.ASCENDING),
                ('date_modified', pymongo.ASCENDING),
            ]
        },
        {
            'unique': False,
            'key_or_list': [
                ('institution_id', pymongo.ASCENDING),
                ('institution_domains', pymongo.ASCENDING),
            ]
        },
        {
            'unique': False,
            'key_or_list': [
                ('institution_id', pymongo.ASCENDING),
                ('institution_email_domains', pymongo.ASCENDING),
            ]
        },
        {
            'unique': False,
            'key_or_list': [
                ('institution_id', pymongo.ASCENDING),
                ('registration_approval', pymongo.ASCENDING),
            ]
        },
    ]

    # Node fields that trigger an update to Solr on save
    SOLR_UPDATE_FIELDS = {
        'title',
        'category',
        'description',
        'visible_contributor_ids',
        'tags',
        'is_fork',
        'is_registration',
        'retraction',
        'embargo',
        'is_public',
        'is_deleted',
        'wiki_pages_current',
        'is_retracted',
        'node_license',
        'primary_institution'
    }

    # Maps category identifier => Human-readable representation for use in
    # titles, menus, etc.
    # Use an OrderedDict so that menu items show in the correct order
    CATEGORY_MAP = OrderedDict([
        ('analysis', 'Analysis'),
        ('communication', 'Communication'),
        ('data', 'Data'),
        ('hypothesis', 'Hypothesis'),
        ('instrumentation', 'Instrumentation'),
        ('methods and measures', 'Methods and Measures'),
        ('procedure', 'Procedure'),
        ('project', 'Project'),
        ('software', 'Software'),
        ('other', 'Other'),
        ('', 'Uncategorized')
    ])

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

    _id = fields.StringField(primary=True)

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow, index=True)
    date_modified = fields.DateTimeField()

    # Privacy
    is_public = fields.BooleanField(default=False, index=True)

    # User mappings
    permissions = fields.DictionaryField()
    visible_contributor_ids = fields.StringField(list=True)

    # Project Organization
    is_bookmark_collection = fields.BooleanField(default=False, index=True)
    is_collection = fields.BooleanField(default=False, index=True)

    is_deleted = fields.BooleanField(default=False, index=True)
    deleted_date = fields.DateTimeField(index=True)

    is_registration = fields.BooleanField(default=False, index=True)
    registered_date = fields.DateTimeField(index=True)
    registered_user = fields.ForeignField('user')

    # A list of all MetaSchemas for which this Node has registered_meta
    registered_schema = fields.ForeignField('metaschema', list=True, default=list)
    # A set of <metaschema._id>: <schema> pairs, where <schema> is a
    # flat set of <question_id>: <response> pairs-- these question ids_above
    # map the the ids in the registrations MetaSchema (see registered_schema).
    # {
    #   <question_id>: {
    #     'value': <value>,
    #     'comments': [
    #       <comment>
    #     ]
    # }
    registered_meta = fields.DictionaryField()
    registration_approval = fields.ForeignField('registrationapproval')
    retraction = fields.ForeignField('retraction')
    embargo = fields.ForeignField('embargo')

    is_fork = fields.BooleanField(default=False, index=True)
    forked_date = fields.DateTimeField(index=True)

    title = fields.StringField(validate=validate_title)
    description = fields.StringField()
    category = fields.StringField(validate=validate_category, index=True)

    node_license = fields.ForeignField('nodelicenserecord')

    # One of 'public', 'private'
    # TODO: Add validator
    comment_level = fields.StringField(default='public')

    wiki_pages_current = fields.DictionaryField()
    wiki_pages_versions = fields.DictionaryField()
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = fields.DictionaryField()
    file_guid_to_share_uuids = fields.DictionaryField()

    creator = fields.ForeignField('user', index=True)
    contributors = fields.ForeignField('user', list=True)
    users_watching_node = fields.ForeignField('user', list=True)

    tags = fields.ForeignField('tag', list=True)

    # Tags for internal use
    system_tags = fields.StringField(list=True)

    nodes = fields.AbstractForeignField(list=True, backref='parent')
    forked_from = fields.ForeignField('node', index=True)
    registered_from = fields.ForeignField('node', index=True)
    root = fields.ForeignField('node', index=True)
    parent_node = fields.ForeignField('node', index=True)

    # The node (if any) used as a template for this node's creation
    template_node = fields.ForeignField('node', index=True)

    piwik_site_id = fields.StringField()

    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    child_node_subscriptions = fields.DictionaryField(default=dict)

    alternative_citations = fields.ForeignField('alternativecitation', list=True)

    _meta = {
        'optimistic': True,
    }

    def __init__(self, *args, **kwargs):

        kwargs.pop('logs', [])

        super(Node, self).__init__(*args, **kwargs)

        if kwargs.get('_is_loaded', False):
            return

        # Ensure when Node is created with tags through API, tags are added to Tag
        tags = kwargs.pop('tags', [])
        for tag in tags:
            self.add_tag(tag, Auth(self.creator), save=False, log=False)

        if self.creator:
            self.contributors.append(self.creator)
            self.set_visible(self.creator, visible=True, log=False)

            # Add default creator permissions
            for permission in CREATOR_PERMISSIONS:
                self.add_permission(self.creator, permission, save=False)

    def __repr__(self):
        return ('<Node(title={self.title!r}, category={self.category!r}) '
                'with _id {self._id!r}>').format(self=self)

    # For Django compatibility
    @property
    def pk(self):
        return self._id

    # For Comment API compatibility
    @property
    def target_type(self):
        """The object "type" used in the OSF v2 API."""
        return 'nodes'

    @property
    def root_target_page(self):
        """The comment page type associated with Nodes."""
        return Comment.OVERVIEW

    def belongs_to_node(self, node_id):
        """Check whether this node matches the specified node."""
        return self._id == node_id

    @property
    def logs(self):
        """ List of logs associated with this node"""
        return NodeLog.find(Q('node', 'eq', self._id)).sort('date')

    @property
    def license(self):
        node_license = self.node_license
        if not node_license and self.parent_node:
            return self.parent_node.license
        return node_license

    @property
    def category_display(self):
        """The human-readable representation of this node's category."""
        return self.CATEGORY_MAP[self.category]

    # We need the following 2 properties in order to serialize related links in NodeRegistrationSerializer
    @property
    def registered_user_id(self):
        """The ID of the user who registered this node if this is a registration, else None.
        """
        if self.registered_user:
            return self.registered_user._id
        return None

    @property
    def registered_from_id(self):
        """The ID of the node that was registered, else None.
        """
        if self.registered_from:
            return self.registered_from._id
        return None

    @property
    def sanction(self):
        sanction = self.registration_approval or self.embargo or self.retraction
        if sanction:
            return sanction
        elif self.parent_node:
            return self.parent_node.sanction
        else:
            return None

    @property
    def is_pending_registration(self):
        if not self.is_registration:
            return False
        if self.registration_approval is None:
            if self.parent_node:
                return self.parent_node.is_pending_registration
            return False
        return self.registration_approval.is_pending_approval

    @property
    def is_registration_approved(self):
        if self.registration_approval is None:
            if self.parent_node:
                return self.parent_node.is_registration_approved
            return False
        return self.registration_approval.is_approved

    @property
    def is_retracted(self):
        if self.retraction is None:
            if self.parent_node:
                return self.parent_node.is_retracted
            return False
        return self.retraction.is_approved

    @property
    def is_pending_retraction(self):
        if self.retraction is None:
            if self.parent_node:
                return self.parent_node.is_pending_retraction
            return False
        return self.retraction.is_pending_approval

    @property
    def embargo_end_date(self):
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.embargo_end_date
            return False
        return self.embargo.embargo_end_date

    @property
    def is_pending_embargo(self):
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.is_pending_embargo
            return False
        return self.embargo.is_pending_approval

    @property
    def is_pending_embargo_for_existing_registration(self):
        """ Returns True if Node has an Embargo pending approval for an
        existing registrations. This is used specifically to ensure
        registrations pre-dating the Embargo feature do not get deleted if
        their respective Embargo request is rejected.
        """
        if self.embargo is None:
            if self.parent_node:
                return self.parent_node.is_pending_embargo_for_existing_registration
            return False
        return self.embargo.pending_registration

    @property
    def private_links(self):
        # TODO: Consumer code assumes this is a list. Hopefully there aren't many links?
        return list(PrivateLink.find(Q('nodes', 'eq', self._id)))

    @property
    def private_links_active(self):
        return [x for x in self.private_links if not x.is_deleted]

    @property
    def private_link_keys_active(self):
        return [x.key for x in self.private_links if not x.is_deleted]

    @property
    def private_link_keys_deleted(self):
        return [x.key for x in self.private_links if x.is_deleted]

    def path_above(self, auth):
        parents = self.parents
        return '/' + '/'.join([p.title if p.can_view(auth) else '-- private project --' for p in reversed(parents)])

    @property
    def ids_above(self):
        parents = self.parents
        return {p._id for p in parents}

    @property
    def nodes_active(self):
        return [x for x in self.nodes if not x.is_deleted]

    @property
    def draft_registrations_active(self):
        drafts = DraftRegistration.find(
            Q('branched_from', 'eq', self)
        )
        for draft in drafts:
            if not draft.registered_node or draft.registered_node.is_deleted:
                yield draft

    @property
    def has_active_draft_registrations(self):
        try:
            next(self.draft_registrations_active)
        except StopIteration:
            return False
        else:
            return True

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
            (user and self.has_permission(user, 'write'))
            or is_api_node
        )

    def active_contributors(self, include=lambda n: True):
        for contrib in self.contributors:
            if contrib.is_active and include(contrib):
                yield contrib

    def is_admin_parent(self, user):
        if self.has_permission(user, 'admin', check_parent=False):
            return True
        if self.parent_node:
            return self.parent_node.is_admin_parent(user)
        return False

    def can_view(self, auth):
        if auth and getattr(auth.private_link, 'anonymous', False):
            return self._id in auth.private_link.nodes

        if not auth and not self.is_public:
            return False

        return (
            self.is_public or
            (auth.user and self.has_permission(auth.user, 'read')) or
            auth.private_key in self.private_link_keys_active or
            self.is_admin_parent(auth.user)
        )

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

    @property
    def forks(self):
        """List of forks of this node"""
        return Node.find(Q('forked_from', 'eq', self._id) &
                         Q('is_deleted', 'eq', False)
                         & Q('is_registration', 'ne', True))

    def add_permission(self, user, permission, save=False):
        """Grant permission to a user.

        :param User user: User to grant permission to
        :param str permission: Permission to grant
        :param bool save: Save changes
        :raises: ValueError if user already has permission
        """
        if user._id not in self.permissions:
            self.permissions[user._id] = [permission]
        else:
            if permission in self.permissions[user._id]:
                raise ValueError('User already has permission {0}'.format(permission))
            self.permissions[user._id].append(permission)
        if save:
            self.save()

    def remove_permission(self, user, permission, save=False):
        """Revoke permission from a user.

        :param User user: User to revoke permission from
        :param str permission: Permission to revoke
        :param bool save: Save changes
        :raises: ValueError if user does not have permission
        """
        try:
            self.permissions[user._id].remove(permission)
        except (KeyError, ValueError):
            raise ValueError('User does not have permission {0}'.format(permission))
        if save:
            self.save()

    def clear_permission(self, user, save=False):
        """Clear all permissions for a user.

        :param User user: User to revoke permission from
        :param bool save: Save changes
        :raises: ValueError if user not in permissions
        """
        try:
            self.permissions.pop(user._id)
        except KeyError:
            raise ValueError(
                'User {0} not in permissions list for node {1}'.format(
                    user._id, self._id,
                )
            )
        if save:
            self.save()

    def set_permissions(self, user, permissions, save=False):
        self.permissions[user._id] = permissions
        if save:
            self.save()

    def has_permission(self, user, permission, check_parent=True):
        """Check whether user has permission.

        :param User user: User to test
        :param str permission: Required permission
        :returns: User has required permission
        """
        if user is None:
            return False
        if permission in self.permissions.get(user._id, []):
            return True
        if permission == 'read' and check_parent:
            return self.is_admin_parent(user)
        return False

    def has_permission_on_children(self, user, permission):
        """Checks if the given user has a given permission on any child nodes
            that are not registrations or deleted
        """
        if self.has_permission(user, permission):
            return True

        for node in self.nodes:
            if not node.primary or node.is_deleted:
                continue

            if node.has_permission_on_children(user, permission):
                return True

        return False

    def has_addon_on_children(self, addon):
        """Checks if a given node has a specific addon on child nodes
            that are not registrations or deleted
        """
        if self.has_addon(addon):
            return True

        for node in self.nodes:
            if not node.primary or node.is_deleted:
                continue

            if node.has_addon_on_children(addon):
                return True

        return False

    def get_permissions(self, user):
        """Get list of permissions for user.

        :param User user: User to check
        :returns: List of permissions
        :raises: ValueError if user not found in permissions
        """
        return self.permissions.get(user._id, [])

    def adjust_permissions(self):
        for key in self.permissions.keys():
            if key not in self.contributors:
                self.permissions.pop(key)

    @property
    def visible_contributors(self):
        return [
            User.load(_id)
            for _id in self.visible_contributor_ids
        ]

    @property
    def parents(self):
        if self.parent_node:
            return [self.parent_node] + self.parent_node.parents
        return []

    @property
    def admin_contributor_ids(self, contributors=None):
        contributor_ids = self.contributors._to_primary_keys()
        admin_ids = set()
        for parent in self.parents:
            admins = [
                user for user, perms in parent.permissions.iteritems()
                if 'admin' in perms
            ]
            admin_ids.update(set(admins).difference(contributor_ids))
        return admin_ids

    @property
    def admin_contributors(self):
        return sorted(
            [User.load(_id) for _id in self.admin_contributor_ids],
            key=lambda user: user.family_name,
        )

    def get_visible(self, user):
        if not self.is_contributor(user):
            raise ValueError(u'User {0} not in contributors'.format(user))
        return user._id in self.visible_contributor_ids

    def update_visible_ids(self, save=False):
        """Update the order of `visible_contributor_ids`. Updating on making
        a contributor visible is more efficient than recomputing order on
        accessing `visible_contributors`.
        """
        self.visible_contributor_ids = [
            contributor._id
            for contributor in self.contributors
            if contributor._id in self.visible_contributor_ids
        ]
        if save:
            self.save()

    def set_visible(self, user, visible, log=True, auth=None, save=False):
        if not self.is_contributor(user):
            raise ValueError(u'User {0} not in contributors'.format(user))
        if visible and user._id not in self.visible_contributor_ids:
            self.visible_contributor_ids.append(user._id)
            self.update_visible_ids(save=False)
        elif not visible and user._id in self.visible_contributor_ids:
            if len(self.visible_contributor_ids) == 1:
                raise ValueError('Must have at least one visible contributor')
            self.visible_contributor_ids.remove(user._id)
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

    def can_comment(self, auth):
        if self.comment_level == 'public':
            return auth.logged_in and (
                self.is_public or
                (auth.user and self.has_permission(auth.user, 'read'))
            )
        return self.is_contributor(auth.user)

    def set_node_license(self, license_id, year, copyright_holders, auth, save=False):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError("Only admins can change a project's license.")
        try:
            node_license = NodeLicense.find_one(
                Q('id', 'eq', license_id)
            )
        except NoResultsFound:
            raise NodeStateError("Trying to update a Node with an invalid license.")
        record = self.node_license
        if record is None:
            record = NodeLicenseRecord(
                node_license=node_license
            )
        record.node_license = node_license
        record.year = year
        record.copyright_holders = copyright_holders or []
        record.save()
        self.node_license = record
        self.add_log(
            action=NodeLog.CHANGED_LICENSE,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'new_license': node_license.name
            },
            auth=auth,
            save=False,
        )

        if save:
            self.save()

    def subscribe_user_to_notifications(self, user):
        """ Update the notification settings for the creator or contributors

        :param user: User to subscribe to notifications
        """
        from website.notifications.utils import to_subscription_key
        from website.notifications.utils import get_global_notification_type
        from website.notifications.model import NotificationSubscription

        events = ['file_updated', 'comments']
        notification_type = 'email_transactional'
        target_id = self._id

        for event in events:
            event_id = to_subscription_key(target_id, event)
            global_event_id = to_subscription_key(user._id, 'global_' + event)
            global_subscription = NotificationSubscription.load(global_event_id)

            subscription = NotificationSubscription.load(event_id)
            if not subscription:
                subscription = NotificationSubscription(_id=event_id, owner=self, event_name=event)
            if global_subscription:
                global_notification_type = get_global_notification_type(global_subscription, user)
                subscription.add_user_to_subscription(user, global_notification_type)
            else:
                subscription.add_user_to_subscription(user, notification_type)
            subscription.save()

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
                raise NodeUpdateError(reason="Registered content cannot be updated", key=key)
            # Title and description have special methods for logging purposes
            if key == 'title':
                if not self.is_bookmark_collection:
                    self.set_title(title=value, auth=auth, save=False)
                else:
                    raise NodeUpdateError(reason='Bookmark collections cannot be renamed.', key=key)
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
                    value.get('id'),
                    value.get('year'),
                    value.get('copyright_holders'),
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
            updated = self.save()
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

    def save(self, *args, **kwargs):
        update_piwik = kwargs.pop('update_piwik', True)
        self.adjust_permissions()

        first_save = not self._is_loaded

        if first_save and self.is_bookmark_collection:
            existing_bookmark_collections = Node.find(
                Q('is_bookmark_collection', 'eq', True) & Q('contributors', 'eq', self.creator._id)
            )
            if existing_bookmark_collections.count() > 0:
                raise NodeStateError("Only one bookmark collection allowed per user.")

        # Bookmark collections are always named 'Bookmarks'
        if self.is_bookmark_collection and self.title != 'Bookmarks':
            self.title = 'Bookmarks'

        is_original = not self.is_registration and not self.is_fork
        if 'suppress_log' in kwargs.keys():
            suppress_log = kwargs['suppress_log']
            del kwargs['suppress_log']
        else:
            suppress_log = False

        self.root = self._root._id
        self.parent_node = self._parent_node

        # If you're saving a property, do it above this super call
        saved_fields = super(Node, self).save(*args, **kwargs)

        if first_save and is_original and not suppress_log:
            # TODO: This logic also exists in self.use_as_template()
            for addon in settings.ADDONS_AVAILABLE:
                if 'node' in addon.added_default:
                    self.add_addon(addon.short_name, auth=None, log=False)

            # Define log fields for non-component project
            log_action = NodeLog.PROJECT_CREATED
            log_params = {
                'node': self._primary_key,
            }

            if getattr(self, 'parent', None):
                # Append log to parent
                self.parent.nodes.append(self)
                self.parent.save()
                log_params.update({'parent_node': self.parent._primary_key})

            # Add log with appropriate fields
            self.add_log(
                log_action,
                params=log_params,
                auth=Auth(user=self.creator),
                log_date=self.date_created,
                save=True,
            )

            if self.creator and settings.ENABLE_NOTIFICATION_SUBSCRIPTION_CREATION:
                self.subscribe_user_to_notifications(user=self.creator)

        # Only update Solr if at least one stored field has changed, and if
        # public or privacy setting has changed
        need_update = bool(self.SOLR_UPDATE_FIELDS.intersection(saved_fields))
        if not self.is_public:
            if first_save or 'is_public' not in saved_fields:
                need_update = False
        if self.is_collection or self.archiving:
            need_update = False
        if need_update:
            self.update_search()

        if 'node_license' in saved_fields:
            children = [c for c in self.get_descendants_recursive(
                include=lambda n: n.node_license is None
            )]
            # this returns generator, that would get unspooled anyways
            if children:
                Node.bulk_update_search(children)

        # This method checks what has changed.
        if settings.PIWIK_HOST and update_piwik:
            piwik_tasks.update_node(self._id, saved_fields)

        # Return expected value for StoredObject::save
        return saved_fields

    ######################################
    # Methods that return a new instance #
    ######################################

    def use_as_template(self, auth, changes=None, top_level=True):
        """Create a new project, using an existing project as a template.

        :param auth: The user to be assigned as creator
        :param changes: A dictionary of changes, keyed by node id, which
                        override the attributes of the template project or its
                        children.
        :return: The `Node` instance created.
        """
        changes = changes or dict()

        # build the dict of attributes to change for the new node
        try:
            attributes = changes[self._id]
            # TODO: explicitly define attributes which may be changed.
        except (AttributeError, KeyError):
            attributes = dict()

        new = self.clone()

        # clear permissions, which are not cleared by the clone method
        new.permissions = {}
        new.visible_contributor_ids = []

        # Clear quasi-foreign fields
        new.wiki_pages_current = {}
        new.wiki_pages_versions = {}
        new.wiki_private_uuids = {}
        new.file_guid_to_share_uuids = {}

        # set attributes which may be overridden by `changes`
        new.is_public = False
        new.description = None

        # apply `changes`
        for attr, val in attributes.iteritems():
            setattr(new, attr, val)

        # set attributes which may NOT be overridden by `changes`
        new.creator = auth.user
        new.template_node = self
        new.add_contributor(contributor=auth.user, permissions=CREATOR_PERMISSIONS, log=False, save=False)
        new.is_fork = False
        new.is_registration = False
        new.piwik_site_id = None
        new.node_license = self.license.copy() if self.license else None

        # If that title hasn't been changed, apply the default prefix (once)
        if (new.title == self.title
                and top_level
                and language.TEMPLATED_FROM_PREFIX not in new.title):
            new.title = ''.join((language.TEMPLATED_FROM_PREFIX, new.title, ))

        # Slight hack - date_created is a read-only field.
        new._fields['date_created'].__set__(
            new,
            datetime.datetime.utcnow(),
            safe=True
        )

        new.save(suppress_log=True)

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
            log_date=new.date_created,
            save=False,
        )

        # add mandatory addons
        # TODO: This logic also exists in self.save()
        for addon in settings.ADDONS_AVAILABLE:
            if 'node' in addon.added_default:
                new.add_addon(addon.short_name, auth=None, log=False)

        # deal with the children of the node, if any
        new.nodes = [
            x.use_as_template(auth, changes, top_level=False)
            for x in self.nodes
            if x.can_view(auth) and not x.is_deleted
        ]

        new.save()
        return new

    ############
    # Pointers #
    ############

    def add_pointer(self, node, auth, save=True):
        """Add a pointer to a node.

        :param Node node: Node to add
        :param Auth auth: Consolidated authorization
        :param bool save: Save changes
        :return: Created pointer
        """
        # Fail if node already in nodes / pointers. Note: cast node and node
        # to primary keys to test for conflicts with both nodes and pointers
        # contained in `self.nodes`.
        if node._id in self.node_ids:
            raise ValueError(
                'Pointer to node {0} already in list'.format(node._id)
            )

        if self.is_registration:
            raise NodeStateError('Cannot add a pointer to a registration')

        # If a folder, prevent more than one pointer to that folder. This will prevent infinite loops on the project organizer.
        already_pointed = node.pointed
        if node.is_collection and len(already_pointed) > 0:
            raise ValueError(
                'Pointer to folder {0} already exists. Only one pointer to any given folder allowed'.format(node._id)
            )
        if node.is_bookmark_collection:
            raise ValueError(
                'Pointer to bookmark collection ({0}) not allowed.'.format(node._id)
            )

        # Append pointer
        pointer = Pointer(node=node)
        pointer.save()
        self.nodes.append(pointer)

        # Add log
        self.add_log(
            action=NodeLog.POINTER_CREATED,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            },
            auth=auth,
            save=False,
        )

        # Optionally save changes
        if save:
            self.save()

        return pointer

    def rm_pointer(self, pointer, auth):
        """Remove a pointer.

        :param Pointer pointer: Pointer to remove
        :param Auth auth: Consolidated authorization
        """
        if pointer not in self.nodes:
            raise ValueError('Node link does not belong to the requested node.')

        # Remove `Pointer` object; will also remove self from `nodes` list of
        # parent node
        Pointer.remove_one(pointer)

        # Add log
        self.add_log(
            action=NodeLog.POINTER_REMOVED,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            },
            auth=auth,
            save=False,
        )

    @property
    def node_ids(self):
        return [
            node._id if node.primary else node.node._id
            for node in self.nodes
        ]

    @property
    def nodes_primary(self):
        return [
            node
            for node in self.nodes
            if node.primary
        ]

    def node_and_primary_descendants(self):
        """Return an iterator for a node and all of its primary (non-pointer) descendants.

        :param node Node: target Node
        """
        return itertools.chain([self], self.get_descendants_recursive(lambda n: n.primary))

    @property
    def depth(self):
        return len(self.parents)

    def next_descendants(self, auth, condition=lambda auth, node: True):
        """
        Recursively find the first set of descedants under a given node that meet a given condition

        returns a list of [(node, [children]), ...]
        """
        ret = []
        for node in self.nodes:
            if condition(auth, node):
                # base case
                ret.append((node, []))
            else:
                ret.append((node, node.next_descendants(auth, condition)))
        ret = [item for item in ret if item[1] or condition(auth, item[0])]  # prune empty branches
        return ret

    def get_descendants_recursive(self, include=lambda n: True):
        for node in self.nodes:
            if include(node):
                yield node
            if node.primary:
                for descendant in node.get_descendants_recursive(include):
                    if include(descendant):
                        yield descendant

    def get_aggregate_logs_query(self, auth):
        ids = [self._id] + [n._id
                            for n in self.get_descendants_recursive()
                            if n.can_view(auth)]
        query = Q('node', 'in', ids) & Q('should_hide', 'ne', True)
        return query

    def get_aggregate_logs_queryset(self, auth):
        query = self.get_aggregate_logs_query(auth)
        return NodeLog.find(query).sort('-date')

    @property
    def nodes_pointer(self):
        return [
            node
            for node in self.nodes
            if not node.primary
        ]

    @property
    def has_pointers_recursive(self):
        """Recursively checks whether the current node or any of its nodes
        contains a pointer.
        """
        if self.nodes_pointer:
            return True
        for node in self.nodes_primary:
            if node.has_pointers_recursive:
                return True
        return False

    @property
    def pointed(self):
        return Pointer.find(Q('node', 'eq', self._id))

    def pointing_at(self, pointed_node_id):
        """This node is pointed at another node.

        :param Node pointed_node_id: The node id of the node being pointed at.
        :return: pointer_id
        """
        for pointer in self.nodes_pointer:
            node_id = pointer.node._id
            if node_id == pointed_node_id:
                return pointer._id
        return None

    def get_points(self, folders=False, deleted=False, resolve=True):
        ret = []
        for each in self.pointed:
            pointer_node = get_pointer_parent(each)
            if not folders and pointer_node.is_collection:
                continue
            if not deleted and pointer_node.is_deleted:
                continue
            if resolve:
                ret.append(pointer_node)
            else:
                ret.append(each)
        return ret

    def resolve(self):
        return self

    def fork_pointer(self, pointer, auth, save=True):
        """Replace a pointer with a fork. If the pointer points to a project,
        fork the project and replace the pointer with a new pointer pointing
        to the fork. If the pointer points to a component, fork the component
        and add it to the current node.

        :param Pointer pointer:
        :param Auth auth:
        :param bool save:
        :return: Forked node
        """
        # Fail if pointer not contained in `nodes`
        try:
            index = self.nodes.index(pointer)
        except ValueError:
            raise ValueError('Pointer {0} not in list'.format(pointer._id))

        # Get pointed node
        node = pointer.node

        # Fork into current node and replace pointer with forked component
        forked = node.fork_node(auth)
        if forked is None:
            raise ValueError('Could not fork node')

        self.nodes[index] = forked

        # Add log
        self.add_log(
            NodeLog.POINTER_FORKED,
            params={
                'parent_node': self.parent_id,
                'node': self._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            },
            auth=auth,
            save=False,
        )

        # Optionally save changes
        if save:
            self.save()
            # Garbage-collect pointer. Note: Must save current node before
            # removing pointer, else remove will fail when trying to remove
            # backref from self to pointer.
            Pointer.remove_one(pointer)

        # Return forked content
        return forked

    def get_recent_logs(self, n=10):
        """Return a list of the n most recent logs, in reverse chronological
        order.

        :param int n: Number of logs to retrieve
        """
        return self.logs.sort('-date')[:n]

    def set_title(self, title, auth, save=False):
        """Set the title of this Node and log it.

        :param str title: The new title.
        :param auth: All the auth information including user, API key.
        """
        #Called so validation does not have to wait until save.
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

    def update_search(self):
        from website import search
        try:
            search.search.update_node(self, bulk=False, async=True)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    @classmethod
    def bulk_update_search(cls, nodes):
        from website import search
        try:
            serialize = functools.partial(search.search.update_node, bulk=True, async=False)
            search.search.bulk_update_nodes(serialize, nodes)
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

    def delete_registration_tree(self, save=False):
        self.is_deleted = True
        if not getattr(self.embargo, 'for_existing_registration', False):
            self.registered_from = None
        if save:
            self.save()
        self.update_search()
        for child in self.nodes_primary:
            child.delete_registration_tree(save=save)

    def remove_node(self, auth, date=None):
        """Marks a node as deleted.

        TODO: Call a hook on addons
        Adds a log to the parent node if applicable

        :param auth: an instance of :class:`Auth`.
        :param date: Date node was removed
        :type date: `datetime.datetime` or `None`
        """
        # TODO: rename "date" param - it's shadowing a global

        if self.is_bookmark_collection:
            raise NodeStateError("Bookmark collections may not be deleted.")

        if not self.can_edit(auth):
            raise PermissionsError('{0!r} does not have permission to modify this {1}'.format(auth.user, self.category or 'node'))

        #if this is a collection, remove all the collections that this is pointing at.
        if self.is_collection:
            for pointed in self.nodes_pointer:
                if pointed.node.is_collection:
                    pointed.node.remove_node(auth=auth)

        if [x for x in self.nodes_primary if not x.is_deleted]:
            raise NodeStateError("Any child components must be deleted prior to deleting this project.")

        # After delete callback
        for addon in self.get_addons():
            message = addon.after_delete(self, auth.user)
            if message:
                status.push_status_message(message, kind='info', trust=False)

        log_date = date or datetime.datetime.utcnow()

        # Add log to parent
        if self.node__parent:
            self.node__parent[0].add_log(
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

        auth_signals.node_deleted.send(self)

        return True

    def fork_node(self, auth, title='Fork of '):
        """Recursively fork a node.

        :param Auth auth: Consolidated authorization
        :param str title: Optional text to prepend to forked title
        :return: Forked node
        """
        user = auth.user

        # Non-contributors can't fork private nodes
        if not (self.is_public or self.has_permission(user, 'read')):
            raise PermissionsError('{0!r} does not have permission to fork node {1!r}'.format(user, self._id))

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)

        if original.is_deleted:
            raise NodeStateError('Cannot fork deleted node.')

        # Note: Cloning a node copies its `wiki_pages_current` and
        # `wiki_pages_versions` fields, but does not clone the underlying
        # database objects to which these dictionaries refer. This means that
        # the cloned node must pass itself to its wiki objects to build the
        # correct URLs to that content.
        forked = original.clone()

        forked.tags = self.tags

        # Recursively fork child nodes
        for node_contained in original.nodes:
            if not node_contained.is_deleted:
                forked_node = None
                try:  # Catch the potential PermissionsError above
                    forked_node = node_contained.fork_node(auth=auth, title='')
                except PermissionsError:
                    pass  # If this exception is thrown omit the node from the result set
                if forked_node is not None:
                    forked.nodes.append(forked_node)

        forked.title = title + forked.title
        forked.is_fork = True
        forked.is_registration = False
        forked.forked_date = when
        forked.forked_from = original
        forked.creator = user
        forked.piwik_site_id = None
        forked.node_license = original.license.copy() if original.license else None

        # Forks default to private status
        forked.is_public = False

        # Clear permissions before adding users
        forked.permissions = {}
        forked.visible_contributor_ids = []

        for citation in self.alternative_citations:
            forked.add_citation(
                auth=auth,
                citation=citation.clone(),
                log=False,
                save=False
            )

        forked.add_contributor(
            contributor=user,
            permissions=CREATOR_PERMISSIONS,
            log=False,
            save=False
        )

        # Need this save in order to access _primary_key
        forked.save()

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
        logs = original.logs
        for log in logs:
            log.clone_node_log(forked._id)

        forked.reload()

        # After fork callback
        for addon in original.get_addons():
            _, message = addon.after_fork(original, forked, user)
            if message:
                status.push_status_message(message, kind='info', trust=True)

        return forked

    def register_node(self, schema, auth, data, parent=None):
        """Make a frozen copy of a node.

        :param schema: Schema object
        :param auth: All the auth information including user, API key.
        :param template: Template name
        :param data: Form data
        :param parent Node: parent registration of registration to be created
        """
        # TODO(lyndsysimon): "template" param is not necessary - use schema.name?
        # NOTE: Admins can register child nodes even if they don't have write access them
        if not self.can_edit(auth=auth) and not self.is_admin_parent(user=auth.user):
            raise PermissionsError(
                'User {} does not have permission '
                'to register this node'.format(auth.user._id)
            )
        if self.is_collection:
            raise NodeStateError("Folders may not be registered")

        when = datetime.datetime.utcnow()

        original = self.load(self._primary_key)

        # Note: Cloning a node copies its `wiki_pages_current` and
        # `wiki_pages_versions` fields, but does not clone the underlying
        # database objects to which these dictionaries refer. This means that
        # the cloned node must pass itself to its wiki objects to build the
        # correct URLs to that content.
        if original.is_deleted:
            raise NodeStateError('Cannot register deleted node.')

        registered = original.clone()

        registered.is_registration = True
        registered.registered_date = when
        registered.registered_user = auth.user
        registered.registered_schema.append(schema)
        registered.registered_from = original
        if not registered.registered_meta:
            registered.registered_meta = {}
        registered.registered_meta[schema._id] = data

        registered.contributors = self.contributors
        registered.forked_from = self.forked_from
        registered.creator = self.creator
        registered.tags = self.tags
        registered.piwik_site_id = None
        registered.primary_institution = self.primary_institution
        registered._affiliated_institutions = self._affiliated_institutions
        registered.alternative_citations = self.alternative_citations
        registered.node_license = original.license.copy() if original.license else None

        registered.save()

        # Clone each log from the original node for this registration.
        logs = original.logs
        for log in logs:
            log.clone_node_log(registered._id)

        registered.is_public = False
        for node in registered.get_descendants_recursive():
            node.is_public = False
            node.save()

        if parent:
            registered._parent_node = parent

        # After register callback
        for addon in original.get_addons():
            _, message = addon.after_register(original, registered, auth.user)
            if message:
                status.push_status_message(message, kind='info', trust=False)

        for node_contained in original.nodes:
            if not node_contained.is_deleted:
                child_registration = node_contained.register_node(
                    schema=schema,
                    auth=auth,
                    data=data,
                    parent=registered,
                )
                if child_registration and not child_registration.primary:
                    registered.nodes.append(child_registration)

        registered.save()

        if settings.ENABLE_ARCHIVER:
            registered.reload()
            project_signals.after_create_registration.send(self, dst=registered, user=auth.user)

        return registered

    def remove_tag(self, tag, auth, save=True):
        if tag in self.tags:
            self.tags.remove(tag)
            self.add_log(
                action=NodeLog.TAG_REMOVED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._primary_key,
                    'tag': tag,
                },
                auth=auth,
                save=False,
            )
            if save:
                self.save()

    def add_tag(self, tag, auth, save=True, log=True):
        if not isinstance(tag, Tag):
            tag_instance = Tag.load(tag)
            if tag_instance is None:
                tag_instance = Tag(_id=tag)
        else:
            tag_instance = tag
        #  should noop if it's not dirty
        tag_instance.save()

        if tag_instance._id not in self.tags:
            self.tags.append(tag_instance)
            if log:
                self.add_log(
                    action=NodeLog.TAG_ADDED,
                    params={
                        'parent_node': self.parent_id,
                        'node': self._primary_key,
                        'tag': tag_instance._id,
                    },
                    auth=auth,
                    save=False,
                )
            if save:
                self.save()

    def add_citation(self, auth, save=False, log=True, citation=None, **kwargs):
        if not citation:
            citation = AlternativeCitation(**kwargs)
        citation.save()
        self.alternative_citations.append(citation)
        citation_dict = {'name': citation.name, 'text': citation.text}
        if log:
            self.add_log(
                action=NodeLog.CITATION_ADDED,
                params={
                    'node': self._primary_key,
                    'citation': citation_dict
                },
                auth=auth,
                save=False
            )
            if save:
                self.save()
        return citation

    def edit_citation(self, auth, instance, save=False, log=True, **kwargs):
        citation = {'name': instance.name, 'text': instance.text}
        new_name = kwargs.get('name', instance.name)
        new_text = kwargs.get('text', instance.text)
        if new_name != instance.name:
            instance.name = new_name
            citation['new_name'] = new_name
        if new_text != instance.text:
            instance.text = new_text
            citation['new_text'] = new_text
        instance.save()
        if log:
            self.add_log(
                action=NodeLog.CITATION_EDITED,
                params={
                    'node': self._primary_key,
                    'citation': citation
                },
                auth=auth,
                save=False
            )
        if save:
            self.save()
        return instance

    def remove_citation(self, auth, instance, save=False, log=True):
        citation = {'name': instance.name, 'text': instance.text}
        self.alternative_citations.remove(instance)
        if log:
            self.add_log(
                action=NodeLog.CITATION_REMOVED,
                params={
                    'node': self._primary_key,
                    'citation': citation
                },
                auth=auth,
                save=False
            )
        if save:
            self.save()

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True):
        user = auth.user if auth else None
        params['node'] = params.get('node') or params.get('project') or self._id
        log = NodeLog(
            action=action,
            user=user,
            foreign_user=foreign_user,
            params=params,
            node=self,
            original_node=params['node']
        )

        if log_date:
            log.date = log_date
        log.save()

        if len(self.logs) == 1:
            self.date_modified = log.date.replace(tzinfo=None)
        else:
            self.date_modified = self.logs[-1].date.replace(tzinfo=None)

        if save:
            self.save()
        if user:
            increment_user_activity_counters(user._primary_key, action, log.date)
        return log

    @classmethod
    def find_for_user(cls, user, subquery=None):
        combined_query = Q('contributors', 'eq', user._id)

        if subquery is not None:
            combined_query = combined_query & subquery
        return cls.find(combined_query)

    @property
    def url(self):
        return '/{}/'.format(self._primary_key)

    def web_url_for(self, view_name, _absolute=False, _guid=False, *args, **kwargs):
        return web_url_for(view_name, pid=self._primary_key, _absolute=_absolute, _guid=_guid, *args, **kwargs)

    def api_url_for(self, view_name, _absolute=False, *args, **kwargs):
        return api_url_for(view_name, pid=self._primary_key, _absolute=_absolute, *args, **kwargs)

    @property
    def absolute_url(self):
        if not self.url:
            logger.error('Node {0} has a parent that is not a project'.format(self._id))
            return None
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def display_absolute_url(self):
        url = self.absolute_url
        if url is not None:
            return re.sub(r'https?:', '', url).strip('/')

    @property
    def api_v2_url(self):
        return reverse('nodes:node-detail', kwargs={'node_id': self._id})

    @property
    def absolute_api_v2_url(self):
        if self.is_registration:
            path = '/registrations/{}/'.format(self._id)
            return api_v2_url(path)
        if self.is_collection:
            path = '/collections/{}/'.format(self._id)
            return api_v2_url(path)
        path = '/nodes/{}/'.format(self._id)
        return api_v2_url(path)

    # used by django and DRF
    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def api_url(self):
        if not self.url:
            logger.error('Node {0} has a parent that is not a project'.format(self._id))
            return None
        return '/api/v1{0}'.format(self.deep_url)

    @property
    def deep_url(self):
        return '/project/{}/'.format(self._primary_key)

    @property
    def linked_nodes_self_url(self):
        return self.absolute_api_v2_url + 'relationships/linked_nodes/'

    @property
    def linked_nodes_related_url(self):
        return self.absolute_api_v2_url + 'linked_nodes/'

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
                contributor.csl_name  # method in auth/model.py which parses the names of authors
                for contributor in self.visible_contributors
            ],
            'publisher': 'Open Science Framework',
            'type': 'webpage',
            'URL': self.display_absolute_url,
        }

        doi = self.get_identifier_value('doi')
        if doi:
            csl['DOI'] = doi

        if self.logs:
            csl['issued'] = datetime_to_csl(self.logs[-1].date)

        return csl

    def author_list(self, and_delim='&'):
        author_names = [
            author.biblio_name
            for author in self.visible_contributors
            if author
        ]
        if len(author_names) < 2:
            return ' {0} '.format(and_delim).join(author_names)
        if len(author_names) > 7:
            author_names = author_names[:7]
            author_names.append('et al.')
            return ', '.join(author_names)
        return u'{0}, {1} {2}'.format(
            ', '.join(author_names[:-1]),
            and_delim,
            author_names[-1]
        )

    @property
    def templated_list(self):
        return Node.find(Q('template_node', 'eq', self._id) & Q('is_deleted', 'ne', True))

    @property
    def _parent_node(self):
        """The parent node, if it exists, otherwise ``None``. Note: this
        property is named `parent_node` rather than `parent` to avoid a
        conflict with the `parent` back-reference created by the `nodes`
        field on this schema.
        """
        try:
            if not self.node__parent[0].is_deleted:
                return self.node__parent[0]
        except IndexError:
            pass
        return None

    @_parent_node.setter
    def _parent_node(self, parent):
        parent.nodes.append(self)
        parent.save()

    @property
    def _root(self):
        if self._parent_node:
            return self._parent_node._root
        else:
            return self

    @property
    def archiving(self):
        job = self.archive_job
        return job and not job.done and not job.archive_tree_finished()

    @property
    def archive_job(self):
        return self.archivejob__active[0] if self.archivejob__active else None

    @property
    def registrations_all(self):
        return Node.find(Q('registered_from', 'eq', self._id))

    @property
    def registrations(self):
        # TODO: This method may be totally unused
        return Node.find(Q('registered_from', 'eq', self._id) & Q('archiving', 'eq', False))

    @property
    def watch_url(self):
        return os.path.join(self.api_url, "watch/")

    @property
    def parent_id(self):
        if self.node__parent:
            return self.node__parent[0]._primary_key
        return None

    @property
    def forked_from_id(self):
        if self.forked_from:
            return self.forked_from._id
        return None

    @property
    def project_or_component(self):
        return 'project' if self.category == 'project' else 'component'

    def is_contributor(self, user):
        return (
            user is not None
            and (
                user._id in self.contributors
            )
        )

    def add_addon(self, addon_name, auth, log=True, *args, **kwargs):
        """Add an add-on to the node. Do nothing if the addon is already
        enabled.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :param bool log: Add a log after adding the add-on
        :return: A boolean, whether the addon was added
        """
        ret = AddonModelMixin.add_addon(self, addon_name, auth=auth,
                                        *args, **kwargs)
        if ret and log:
            config = settings.ADDONS_AVAILABLE_DICT[addon_name]
            self.add_log(
                action=NodeLog.ADDON_ADDED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'addon': config.full_name,
                },
                auth=auth,
                save=False,
            )
            self.save()  # TODO: here, or outside the conditional? @mambocab
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
        ret = super(Node, self).delete_addon(addon_name, auth, _force)
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
            for child in self.nodes:
                if not child.is_deleted:
                    messages.extend(
                        child.callback(
                            callback, recursive, *args, **kwargs
                        )
                    )

        return messages

    def replace_contributor(self, old, new):
        for i, contrib in enumerate(self.contributors):
            if contrib._primary_key == old._primary_key:
                self.contributors[i] = new
                # Remove unclaimed record for the project
                if self._primary_key in old.unclaimed_records:
                    del old.unclaimed_records[self._primary_key]
                    old.save()
                for permission in self.get_permissions(old):
                    self.add_permission(new, permission)
                self.permissions.pop(old._id)
                if old._id in self.visible_contributor_ids:
                    self.visible_contributor_ids[self.visible_contributor_ids.index(old._id)] = new._id
                return True
        return False

    def remove_contributor(self, contributor, auth, log=True):
        """Remove a contributor from this node.

        :param contributor: User object, the contributor to be removed
        :param auth: All the auth information including user, API key.
        """
        # remove unclaimed record if necessary
        if self._primary_key in contributor.unclaimed_records:
            del contributor.unclaimed_records[self._primary_key]

        self.contributors.remove(contributor._id)

        self.clear_permission(contributor)
        if contributor._id in self.visible_contributor_ids:
            self.visible_contributor_ids.remove(contributor._id)

        if not self.visible_contributor_ids:
            return False

        # Node must have at least one registered admin user
        admins = list(self.get_admin_contributors(self.contributors))
        if not admins:
            return False

        # Clear permissions for removed user
        self.permissions.pop(contributor._id, None)

        # After remove callback
        for addon in self.get_addons():
            message = addon.after_remove_contributor(self, contributor, auth)
            if message:
                # Because addons can return HTML strings, addons are responsible for markupsafe-escaping any messages returned
                status.push_status_message(message, kind='info', trust=True)

        if log:
            self.add_log(
                action=NodeLog.CONTRIB_REMOVED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'contributors': [contributor._id],
                },
                auth=auth,
                save=False,
            )

        self.save()

        #send signal to remove this user from project subscriptions
        auth_signals.contributor_removed.send(contributor, node=self)

        return True

    def remove_contributors(self, contributors, auth=None, log=True, save=False):

        results = []
        removed = []

        for contrib in contributors:
            outcome = self.remove_contributor(
                contributor=contrib, auth=auth, log=False,
            )
            results.append(outcome)
            if outcome:
                project_signals.contributor_removed.send(self, user=contrib)
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

        if False in results:
            return False

        return True

    def update_contributor(self, user, permission, visible, auth, save=False):
        """ TODO: this method should be updated as a replacement for the main loop of
        Node#manage_contributors. Right now there are redundancies, but to avoid major
        feature creep this will not be included as this time.

        Also checks to make sure unique admin is not removing own admin privilege.
        """
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError("Only admins can modify contributor permissions")
        permissions = expand_permissions(permission) or DEFAULT_CONTRIBUTOR_PERMISSIONS
        admins = [contrib for contrib in self.contributors if self.has_permission(contrib, 'admin') and contrib.is_active]
        if not len(admins) > 1:
            # has only one admin
            admin = admins[0]
            if admin == user and ADMIN not in permissions:
                raise NodeStateError('{} is the only admin.'.format(user.fullname))
        if user not in self.contributors:
            raise ValueError(
                'User {0} not in contributors'.format(user.fullname)
            )
        if permission:
            permissions = expand_permissions(permission)
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
                with TokuTransaction():
                    if ['read'] in permissions_changed.values():
                        project_signals.write_permissions_revoked.send(self)
        if visible is not None:
            self.set_visible(user, visible, auth=auth, save=save)
            self.update_visible_ids()

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
        with TokuTransaction():
            users = []
            user_ids = []
            permissions_changed = {}
            visibility_removed = []
            to_retain = []
            to_remove = []
            for user_dict in user_dicts:
                user = User.load(user_dict['id'])
                if user is None:
                    raise ValueError('User not found')
                if user not in self.contributors:
                    raise ValueError(
                        'User {0} not in contributors'.format(user.fullname)
                    )
                permissions = expand_permissions(user_dict['permission'])
                if set(permissions) != set(self.get_permissions(user)):
                    self.set_permissions(user, permissions, save=False)
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

            for user in self.contributors:
                if user._id in user_ids:
                    to_retain.append(user)
                else:
                    to_remove.append(user)

            admins = list(self.get_admin_contributors(users))
            if users is None or not admins:
                raise ValueError(
                    'Must have at least one registered admin contributor'
                )

            if to_retain != users:
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

            self.contributors = users

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
            # Update list of visible IDs
            self.update_visible_ids()
            if save:
                self.save()

        with TokuTransaction():
            if to_remove or permissions_changed and ['read'] in permissions_changed.values():
                project_signals.write_permissions_revoked.send(self)

    def add_contributor(self, contributor, permissions=None, visible=True,
                        auth=None, log=True, save=False):
        """Add a contributor to the project.

        :param User contributor: The contributor to be added
        :param list permissions: Permissions to grant to the contributor
        :param bool visible: Contributor is visible in project dashboard
        :param Auth auth: All the auth information including user, API key
        :param bool log: Add log to self
        :param bool save: Save after adding contributor
        :returns: Whether contributor was added
        """
        MAX_RECENT_LENGTH = 15

        # If user is merged into another account, use master account
        contrib_to_add = contributor.merged_by if contributor.is_merged else contributor
        if contrib_to_add not in self.contributors:

            self.contributors.append(contrib_to_add)
            if visible:
                self.set_visible(contrib_to_add, visible=True, log=False)

            # Add default contributor permissions
            permissions = permissions or DEFAULT_CONTRIBUTOR_PERMISSIONS
            for permission in permissions:
                self.add_permission(contrib_to_add, permission, save=False)

            # Add contributor to recently added list for user
            if auth is not None:
                user = auth.user
                if contrib_to_add in user.recently_added:
                    user.recently_added.remove(contrib_to_add)
                user.recently_added.insert(0, contrib_to_add)
                while len(user.recently_added) > MAX_RECENT_LENGTH:
                    user.recently_added.pop()

            if contrib_to_add.is_registered and settings.ENABLE_NOTIFICATION_SUBSCRIPTION_CREATION:
                self.subscribe_user_to_notifications(contrib_to_add)

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

            project_signals.contributor_added.send(self, contributor=contributor, auth=auth)

            return True

        # Permissions must be overridden if changed when contributor is added to parent he/she is already on a child of.
        elif contrib_to_add in self.contributors and permissions is not None:
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

    def add_unregistered_contributor(self, fullname, email, auth,
                                     permissions=None, save=False):
        """Add a non-registered contributor to the project.

        :param str fullname: The full name of the person.
        :param str email: The email address of the person.
        :param Auth auth: Auth object for the user adding the contributor.
        :returns: The added contributor
        :raises: DuplicateEmailError if user with given email is already in the database.
        """
        # Create a new user record
        contributor = User.create_unregistered(fullname=fullname, email=email)

        contributor.add_unclaimed_record(node=self, referrer=auth.user,
            given_name=fullname, email=email)
        try:
            contributor.save()
        except ValidationValueError:  # User with same email already exists
            contributor = get_user(email=email)
            # Unregistered users may have multiple unclaimed records, so
            # only raise error if user is registered.
            if contributor.is_registered or self.is_contributor(contributor):
                raise
            contributor.add_unclaimed_record(node=self, referrer=auth.user,
                given_name=fullname, email=email)
            contributor.save()

        self.add_contributor(
            contributor, permissions=permissions, auth=auth,
            log=True, save=False,
        )
        self.save()
        return contributor

    def set_privacy(self, permissions, auth=None, log=True, save=True, meeting_creation=False):
        """Set the permissions for this node. Also, based on meeting_creation, queues an email to user about abilities of
            public projects.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        :param bool meeting_creation: Whther this was creayed due to a meetings email.
        """
        if auth and not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Must be an admin to change privacy settings.')
        if permissions == 'public' and not self.is_public:
            if self.is_registration:
                if self.is_pending_embargo:
                    raise NodeStateError("A registration with an unapproved embargo cannot be made public.")
                elif self.is_pending_registration:
                    raise NodeStateError("An unapproved registration cannot be made public.")
                elif self.embargo_end_date:
                    raise NodeStateError("An embargoed registration cannot be made public.")
            self.is_public = True
        elif permissions == 'private' and self.is_public:
            if self.is_registration and not self.is_pending_embargo:
                raise NodeStateError("Public registrations must be withdrawn, not made private.")
            else:
                self.is_public = False
        else:
            return False

        # After set permissions callback
        for addon in self.get_addons():
            message = addon.after_set_privacy(self, permissions)
            if message:
                status.push_status_message(message, kind='info', trust=False)

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

    def admin_public_wiki(self, user):
        return (
            self.has_addon('wiki') and
            self.has_permission(user, 'admin') and
            self.is_public
        )

    def include_wiki_settings(self, user):
        """Check if node meets requirements to make publicly editable."""
        return (
            self.admin_public_wiki(user) or
            any(
                each.admin_public_wiki(user)
                for each in self.get_descendants_recursive()
            )
        )

    # TODO: Move to wiki add-on
    def get_wiki_page(self, name=None, version=None, id=None):
        from website.addons.wiki.model import NodeWikiPage

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

    # TODO: Move to wiki add-on
    def update_node_wiki(self, name, content, auth):
        """Update the node's wiki page with new content.

        :param page: A string, the page's name, e.g. ``"home"``.
        :param content: A string, the posted content.
        :param auth: All the auth information including user, API key.
        """
        from website.addons.wiki.model import NodeWikiPage

        name = (name or '').strip()
        key = to_mongo_key(name)
        has_comments = False

        if key not in self.wiki_pages_current:
            if key in self.wiki_pages_versions:
                version = len(self.wiki_pages_versions[key]) + 1
            else:
                version = 1
        else:
            current = NodeWikiPage.load(self.wiki_pages_current[key])
            current.is_current = False
            version = current.version + 1
            current.save()
            if Comment.find(Q('root_target', 'eq', current._id)).count() > 0:
                has_comments = True

        new_page = NodeWikiPage(
            page_name=name,
            version=version,
            user=auth.user,
            is_current=True,
            node=self,
            content=content
        )
        new_page.save()

        if has_comments:
            Comment.update(Q('root_target', 'eq', current._id), data={'root_target': Guid.load(new_page._id)})
            Comment.update(Q('target', 'eq', current._id), data={'target': Guid.load(new_page._id)})

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
        from website.addons.wiki.exceptions import (
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
            save=False,
        )
        self.save()

    def delete_node_wiki(self, name, auth):
        name = (name or '').strip()
        key = to_mongo_key(name)
        page = self.get_wiki_page(key)

        del self.wiki_pages_current[key]

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

    def get_stats(self, detailed=False):
        if detailed:
            raise NotImplementedError(
                'Detailed stats exist, but are not yet implemented.'
            )
        else:
            return get_basic_counters('node:%s' % self._primary_key)

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

    def _initiate_retraction(self, user, justification=None):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param justification: Justification, if given, for retraction
        """

        retraction = Retraction(
            initiated_by=user,
            justification=justification or None,  # make empty strings None
            state=Retraction.UNAPPROVED
        )
        retraction.save()  # Save retraction so it has a primary key
        self.retraction = retraction
        self.save()  # Set foreign field reference Node.retraction
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            retraction.add_authorizer(admin, node)
        retraction.save()  # Save retraction approval state
        return retraction

    def retract_registration(self, user, justification=None, save=True):
        """Retract public registration. Instantiate new Retraction object
        and associate it with the respective registration.
        """

        if not self.is_registration or (not self.is_public and not (self.embargo_end_date or self.is_pending_embargo)):
            raise NodeStateError('Only public or embargoed registrations may be withdrawn.')

        if self.root is not self:
            raise NodeStateError('Withdrawal of non-parent registrations is not permitted.')

        retraction = self._initiate_retraction(user, justification)
        self.registered_from.add_log(
            action=NodeLog.RETRACTION_INITIATED,
            params={
                'node': self.registered_from_id,
                'registration': self._id,
                'retraction_id': retraction._id,
            },
            auth=Auth(user),
        )
        self.retraction = retraction
        if save:
            self.save()

    def _is_embargo_date_valid(self, end_date):
        today = datetime.datetime.utcnow()
        if (end_date - today) >= settings.EMBARGO_END_DATE_MIN:
            if (end_date - today) <= settings.EMBARGO_END_DATE_MAX:
                return True
        return False

    def _initiate_embargo(self, user, end_date, for_existing_registration=False, notify_initiator_on_complete=False):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param end_date: Date when the registration should be made public
        """
        embargo = Embargo(
            initiated_by=user,
            end_date=datetime.datetime.combine(end_date, datetime.datetime.min.time()),
            for_existing_registration=for_existing_registration,
            notify_initiator_on_complete=notify_initiator_on_complete
        )
        embargo.save()  # Save embargo so it has a primary key
        self.embargo = embargo
        self.save()  # Set foreign field reference Node.embargo
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            embargo.add_authorizer(admin, node)
        embargo.save()  # Save embargo's approval_state
        return embargo

    def embargo_registration(self, user, end_date, for_existing_registration=False, notify_initiator_on_complete=False):
        """Enter registration into an embargo period at end of which, it will
        be made public
        :param user: User initiating the embargo
        :param end_date: Date when the registration should be made public
        :raises: NodeStateError if Node is not a registration
        :raises: PermissionsError if user is not an admin for the Node
        :raises: ValidationValueError if end_date is not within time constraints
        """

        if not self.is_registration:
            raise NodeStateError('Only registrations may be embargoed')
        if not self.has_permission(user, 'admin'):
            raise PermissionsError('Only admins may embargo a registration')
        if not self._is_embargo_date_valid(end_date):
            raise ValidationValueError('Embargo end date must be more than one day in the future')

        embargo = self._initiate_embargo(user, end_date, for_existing_registration=for_existing_registration, notify_initiator_on_complete=notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.EMBARGO_INITIATED,
            params={
                'node': self.registered_from_id,
                'registration': self._id,
                'embargo_id': embargo._id,
            },
            auth=Auth(user),
            save=True,
        )
        if self.is_public:
            self.set_privacy('private', Auth(user))

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

        :param bool unique_users: If True, a given admin will only be yielded once
            during iteration.
        """
        visited_user_ids = []
        for node in self.node_and_primary_descendants(*args, **kwargs):
            for contrib in node.contributors:
                if node.has_permission(contrib, ADMIN) and contrib.is_active:
                    if unique_users:
                        if contrib._id not in visited_user_ids:
                            visited_user_ids.append(contrib._id)
                            yield (contrib, node)
                    else:
                        yield (contrib, node)

    def get_admin_contributors(self, users):
        """Return a set of all admin contributors for this node. Excludes contributors on node links and
        inactive users.
        """
        return (
            user for user in users
            if self.has_permission(user, 'admin') and
            user.is_active)

    def _initiate_approval(self, user, notify_initiator_on_complete=False):
        end_date = datetime.datetime.now() + settings.REGISTRATION_APPROVAL_TIME
        approval = RegistrationApproval(
            initiated_by=user,
            end_date=end_date,
            notify_initiator_on_complete=notify_initiator_on_complete
        )
        approval.save()  # Save approval so it has a primary key
        self.registration_approval = approval
        self.save()  # Set foreign field reference Node.registration_approval
        admins = self.get_admin_contributors_recursive(unique_users=True)
        for (admin, node) in admins:
            approval.add_authorizer(admin, node=node)
        approval.save()  # Save approval's approval_state
        return approval

    def require_approval(self, user, notify_initiator_on_complete=False):
        if not self.is_registration:
            raise NodeStateError('Only registrations can require registration approval')
        if not self.has_permission(user, 'admin'):
            raise PermissionsError('Only admins can initiate a registration approval')

        approval = self._initiate_approval(user, notify_initiator_on_complete)

        self.registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_INITIATED,
            params={
                'node': self.registered_from_id,
                'registration': self._id,
                'registration_approval_id': approval._id,
            },
            auth=Auth(user),
            save=True,
        )

    @property
    def watches(self):
        return WatchConfig.find(Q('node', 'eq', self._id))

    institution_id = fields.StringField(unique=True, index=True)
    institution_domains = fields.StringField(list=True)
    institution_auth_url = fields.StringField(validate=URLValidator())
    institution_logo_name = fields.StringField()
    institution_email_domains = fields.StringField(list=True)
    institution_banner_name = fields.StringField()

    @classmethod
    def find(cls, query=None, allow_institution=False, **kwargs):
        if not allow_institution:
            query = (query & Q('institution_id', 'eq', None)) if query else Q('institution_id', 'eq', None)
        return super(Node, cls).find(query, **kwargs)

    @classmethod
    def find_one(cls, query=None, allow_institution=False, **kwargs):
        if not allow_institution:
            query = (query & Q('institution_id', 'eq', None)) if query else Q('institution_id', 'eq', None)
        return super(Node, cls).find_one(query, **kwargs)

    @classmethod
    def find_by_institution(cls, inst, query=None):
        inst_node = inst.node
        query = query & Q('_primary_institution', 'eq', inst_node)
        return cls.find(query, allow_institution=True)

    # Primary institution node is attached to
    _primary_institution = fields.ForeignField('node')

    @property
    def primary_institution(self):
        '''
        Should behave as if this was a foreign field pointing to Institution
        :return: this node's _primary_institution wrapped with Institution.
        '''
        return Institution(self._primary_institution) if self._primary_institution else None

    @primary_institution.setter
    def primary_institution(self, institution):
        self._primary_institution = institution.node if institution else None

    _affiliated_institutions = fields.ForeignField('node', list=True)

    @property
    def affiliated_institutions(self):
        '''
        Should behave as if this was a foreign field pointing to Institution
        :return: this node's _affiliated_institutions wrapped with Institution as a list.
        '''
        return AffiliatedInstitutionsList([Institution(node) for node in self._affiliated_institutions], obj=self, private_target='_affiliated_institutions')

    def add_primary_institution(self, user, inst, log=True):
        if not isinstance(inst, Institution):
            raise TypeError
        if not user.is_affiliated_with_institution(inst):
            raise UserNotAffiliatedError('User is not affiliated with {}'.format(inst.name))
        if inst == self.primary_institution:
            return False
        previous = self.primary_institution if self.primary_institution else None
        self.primary_institution = inst
        if inst not in self.affiliated_institutions:
            self.affiliated_institutions.append(inst)
        if log:
            self.add_log(
                action=NodeLog.PRIMARY_INSTITUTION_CHANGED,
                params={
                    'node': self._primary_key,
                    'institution': {
                        'id': inst._id,
                        'name': inst.name
                    },
                    'previous_institution': {
                        'id': previous._id if previous else None,
                        'name': previous.name if previous else 'None'
                    }
                },
                auth=Auth(user)
            )
        return True

    def remove_primary_institution(self, user, log=True):
        inst = self.primary_institution
        if not inst:
            return False
        self.primary_institution = None
        if inst in self.affiliated_institutions:
            self.affiliated_institutions.remove(inst)
        if log:
            self.add_log(
                action=NodeLog.PRIMARY_INSTITUTION_REMOVED,
                params={
                    'node': self._primary_key,
                    'institution': {
                        'id': inst._id,
                        'name': inst.name
                    }
                },
                auth=Auth(user)
            )
        return True

    def institution_url(self):
        return self.absolute_api_v2_url + 'institution/'

    def institution_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/institution/'


@Node.subscribe('before_save')
def validate_permissions(schema, instance):
    """Ensure that user IDs in `contributors` and `permissions` match.

    """
    node = instance
    contributor_ids = set([user._id for user in node.contributors])
    permission_ids = set(node.permissions.keys())
    mismatched_contributors = contributor_ids.difference(permission_ids)
    if mismatched_contributors:
        raise ValidationValueError(
            'Contributors {0} missing from `permissions` on node {1}'.format(
                ', '.join(mismatched_contributors),
                node._id,
            )
        )
    mismatched_permissions = permission_ids.difference(contributor_ids)
    if mismatched_permissions:
        raise ValidationValueError(
            'Permission keys {0} missing from `contributors` on node {1}'.format(
                ', '.join(mismatched_contributors),
                node._id,
            )
        )


@Node.subscribe('before_save')
def validate_visible_contributors(schema, instance):
    """Ensure that user IDs in `contributors` and `visible_contributor_ids`
    match.

    """
    node = instance
    for user_id in node.visible_contributor_ids:
        if user_id not in node.contributors:
            raise ValidationValueError(
                ('User {0} is in `visible_contributor_ids` but not in '
                 '`contributors` on node {1}').format(
                    user_id,
                    node._id,
                )
            )


class WatchConfig(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    node = fields.ForeignField('Node')
    digest = fields.BooleanField(default=False)
    immediate = fields.BooleanField(default=False)

    def __repr__(self):
        return '<WatchConfig(node="{self.node}")>'.format(self=self)


class PrivateLink(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    key = fields.StringField(required=True, unique=True)
    name = fields.StringField()
    is_deleted = fields.BooleanField(default=False)
    anonymous = fields.BooleanField(default=False)

    nodes = fields.ForeignField('node', list=True)
    creator = fields.ForeignField('user')

    @property
    def node_ids(self):
        node_ids = [node._id for node in self.nodes]
        return node_ids

    def node_scale(self, node):
        # node may be None if previous node's parent is deleted
        if node is None or node.parent_id not in self.node_ids:
            return -40
        else:
            offset = 20 if node.parent_node is not None else 0
            return offset + self.node_scale(node.parent_node)

    def to_json(self):
        return {
            "id": self._id,
            "date_created": iso8601format(self.date_created),
            "key": self.key,
            "name": sanitize.unescape_entities(self.name),
            "creator": {'fullname': self.creator.fullname, 'url': self.creator.profile_url},
            "nodes": [{'title': x.title, 'url': x.url, 'scale': str(self.node_scale(x)) + 'px', 'category': x.category}
                      for x in self.nodes if not x.is_deleted],
            "anonymous": self.anonymous
        }


class Sanction(StoredObject):
    """Sanction class is a generic way to track approval states"""
    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    # Neither approved not cancelled
    UNAPPROVED = 'unapproved'
    # Has approval
    APPROVED = 'approved'
    # Rejected by at least one person
    REJECTED = 'rejected'
    # Embargo has been completed
    COMPLETED = 'completed'

    state = fields.StringField(
        default=UNAPPROVED,
        validate=validators.choice_in((
            UNAPPROVED,
            APPROVED,
            REJECTED,
            COMPLETED,
        ))
    )

    DISPLAY_NAME = 'Sanction'
    # SHORT_NAME must correspond with the associated foreign field to query against,
    # e.g. Node.find_one(Q(sanction.SHORT_NAME, 'eq', sanction))
    SHORT_NAME = 'sanction'

    APPROVAL_NOT_AUTHORIZED_MESSAGE = 'This user is not authorized to approve this {DISPLAY_NAME}'
    APPROVAL_INVALID_TOKEN_MESSAGE = 'Invalid approval token provided for this {DISPLAY_NAME}.'
    REJECTION_NOT_AUTHORIZED_MESSAEGE = 'This user is not authorized to reject this {DISPLAY_NAME}'
    REJECTION_INVALID_TOKEN_MESSAGE = 'Invalid rejection token provided for this {DISPLAY_NAME}.'

    # Controls whether or not the Sanction needs unanimous approval or just a single approval
    ANY = 'any'
    UNANIMOUS = 'unanimous'
    mode = UNANIMOUS

    initiation_date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    # Expiration date-- Sanctions in the UNAPPROVED state that are older than their end_date
    # are automatically made ACTIVE by a daily cron job
    # Use end_date=None for a non-expiring Sanction
    end_date = fields.DateTimeField(default=None)

    # Sanction subclasses must have an initiated_by field
    # initiated_by = fields.ForeignField('user', backref='initiated')

    approval_state = fields.DictionaryField()

    def __repr__(self):
        return '<Sanction(end_date={self.end_date!r}) with _id {self._id!r}>'.format(self=self)

    @property
    def is_pending_approval(self):
        return self.state == Sanction.UNAPPROVED

    @property
    def is_approved(self):
        return self.state == Sanction.APPROVED

    @property
    def is_rejected(self):
        return self.state == Sanction.REJECTED

    def approve(self, user):
        raise NotImplementedError("Sanction subclasses must implement an approve method.")

    def reject(self, user):
        raise NotImplementedError("Sanction subclasses must implement an approve method.")

    def _on_reject(self, user):
        """Callback for rejection of a Sanction

        :param User user:
        """
        raise NotImplementedError('Sanction subclasses must implement an #_on_reject method')

    def _on_complete(self, user):
        """Callback for when a Sanction has approval and enters the ACTIVE state

        :param User user:
        """
        raise NotImplementedError('Sanction subclasses must implement an #_on_complete method')

    def forcibly_reject(self):
        self.state = Sanction.REJECTED


class TokenApprovableSanction(Sanction):

    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    def _validate_authorizer(self, user):
        """Subclasses may choose to provide extra restrictions on who can be an authorizer

        :return Boolean: True if user is allowed to be an authorizer else False
        """
        return True
    def add_authorizer(self, user, node, approved=False, save=False):

        """Add an admin user to this Sanction's approval state.

        :param User user: User to add.
        :param Node registration: The pending registration node.
        :param bool approved: Whether `user` has approved.
        :param bool save: Whether to save this object.
        """
        valid = self._validate_authorizer(user)
        if valid and user._id not in self.approval_state:
            self.approval_state[user._id] = {
                'has_approved': approved,
                'node_id': node._id,
                'approval_token': tokens.encode(
                    {
                        'user_id': user._id,
                        'sanction_id': self._id,
                        'action': 'approve_{}'.format(self.SHORT_NAME)
                    }
                ),
                'rejection_token': tokens.encode(
                    {
                        'user_id': user._id,
                        'sanction_id': self._id,
                        'action': 'reject_{}'.format(self.SHORT_NAME)
                    }
                ),
            }
            if save:
                self.save()
            return True
        return False

    def remove_authorizer(self, user, save=False):
        """Remove a user as an authorizer

        :param User user:
        :return Boolean: True if user is removed else False
        """
        if user._id not in self.approval_state:
            return False

        del self.approval_state[user._id]
        if save:
            self.save()
        return True

    def _on_approve(self, user, token):
        """Callback for when a single user approves a Sanction. Calls #_on_complete under two conditions:
        - mode is ANY and the Sanction has not already been cancelled
        - mode is UNANIMOUS and all users have given approval

        :param User user:
        :param str token: user's approval token
        """
        if self.mode == self.ANY or all(authorizer['has_approved'] for authorizer in self.approval_state.values()):
            self.state = Sanction.APPROVED
            self._on_complete(user)

    def token_for_user(self, user, method):
        """
        :param str method: 'approval' | 'rejection'
        """
        try:
            user_state = self.approval_state[user._id]
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        return user_state['{0}_token'.format(method)]

    def approve(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['approval_token'] != token:
                raise InvalidSanctionApprovalToken(self.APPROVAL_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(self.APPROVAL_NOT_AUTHORIZED_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        self.approval_state[user._id]['has_approved'] = True
        self._on_approve(user, token)

    def reject(self, user, token):
        """Cancels sanction if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['rejection_token'] != token:
                raise InvalidSanctionRejectionToken(self.REJECTION_INVALID_TOKEN_MESSAGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        except KeyError:
            raise PermissionsError(self.REJECTION_NOT_AUTHORIZED_MESSAEGE.format(DISPLAY_NAME=self.DISPLAY_NAME))
        self.state = Sanction.REJECTED
        self._on_reject(user)

    def _notify_authorizer(self, user, node):
        pass

    def _notify_non_authorizer(self, user, node):
        pass

    def ask(self, group):
        """
        :param list group: List of (user, node) tuples containing contributors to notify about the
        sanction.
        """
        for contrib, node in group:
            if contrib._id in self.approval_state:
                self._notify_authorizer(contrib, node)
            else:
                self._notify_non_authorizer(contrib, node)


class EmailApprovableSanction(TokenApprovableSanction):

    # Tell modularodm not to attach backends
    _meta = {
        'abstract': True,
    }

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = None

    VIEW_URL_TEMPLATE = ''
    APPROVE_URL_TEMPLATE = ''
    REJECT_URL_TEMPLATE = ''

    # A flag to conditionally run a callback on complete
    notify_initiator_on_complete = fields.BooleanField(default=False)
    # Store a persistant copy of urls for use when needed outside of a request context.
    # This field gets automagically updated whenever models approval_state is modified
    # and the model is saved
    # {
    #   'abcde': {
    #     'approve': [APPROVAL_URL],
    #     'reject': [REJECT_URL],
    #   }
    # }
    stashed_urls = fields.DictionaryField(default=dict)

    @staticmethod
    def _format_or_empty(template, context):
        if context:
            return template.format(**context)
        return ''

    def _view_url(self, user_id, node):
        return self._format_or_empty(self.VIEW_URL_TEMPLATE, self._view_url_context(user_id, node))

    def _view_url_context(self, user_id, node):
        return None

    def _approval_url(self, user_id):
        return self._format_or_empty(self.APPROVE_URL_TEMPLATE, self._approval_url_context(user_id))

    def _approval_url_context(self, user_id):
        return None

    def _rejection_url(self, user_id):
        return self._format_or_empty(self.REJECT_URL_TEMPLATE, self._rejection_url_context(user_id))

    def _rejection_url_context(self, user_id):
        return None

    def _send_approval_request_email(self, user, template, context):
        mails.send_mail(
            user.username,
            template,
            user=user,
            **context
        )

    def _email_template_context(self, user, node, is_authorizer=False):
        return {}

    def _notify_authorizer(self, authorizer, node):
        context = self._email_template_context(authorizer, node, is_authorizer=True)
        if self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(authorizer, self.AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

    def _notify_non_authorizer(self, user, node):
        context = self._email_template_context(user, node)
        if self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE:
            self._send_approval_request_email(user, self.NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE, context)
        else:
            raise NotImplementedError

    def add_authorizer(self, user, node, **kwargs):
        super(EmailApprovableSanction, self).add_authorizer(user, node, **kwargs)
        self.stashed_urls[user._id] = {
            'view': self._view_url(user._id, node),
            'approve': self._approval_url(user._id),
            'reject': self._rejection_url(user._id)
        }
        self.save()

    def _notify_initiator(self):
        raise NotImplementedError

    def _on_complete(self, *args):
        if self.notify_initiator_on_complete:
            self._notify_initiator()


class PreregCallbackMixin(object):

    def _notify_initiator(self):
        registration = self._get_registration()
        prereg_schema = prereg_utils.get_prereg_schema()

        draft = DraftRegistration.find_one(
            Q('registered_node', 'eq', registration)
        )

        if prereg_schema in registration.registered_schema:
            mails.send_mail(
                draft.initiator.username,
                mails.PREREG_CHALLENGE_ACCEPTED,
                user=draft.initiator,
                registration_url=registration.absolute_url,
                mimetype='html'
            )

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        registration = self._get_registration()
        prereg_schema = prereg_utils.get_prereg_schema()
        if prereg_schema in registration.registered_schema:
            return {
                'custom_message': ' as part of the Preregistration Challenge (https://cos.io/prereg)'
            }
        else:
            return {}

class Embargo(PreregCallbackMixin, EmailApprovableSanction):
    """Embargo object for registrations waiting to go public."""

    DISPLAY_NAME = 'Embargo'
    SHORT_NAME = 'embargo'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_EMBARGO_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user')
    for_existing_registration = fields.BooleanField(default=False)

    @property
    def is_completed(self):
        return self.state == self.COMPLETED

    @property
    def embargo_end_date(self):
        if self.state == self.APPROVED:
            return self.end_date
        return False

    # NOTE(hrybacki): Old, private registrations are grandfathered and do not
    # require to be made public or embargoed. This field differentiates them
    # from new registrations entering into an embargo field which should not
    # show up in any search related fields.
    @property
    def pending_registration(self):
        return not self.for_existing_registration and self.is_pending_approval

    def __repr__(self):
        parent_registration = None
        try:
            parent_registration = Node.find_one(Q('embargo', 'eq', self))
        except NoResultsFound:
            pass
        return ('<Embargo(parent_registration={0}, initiated_by={1}, '
                'end_date={2}) with _id {3}>').format(
            parent_registration,
            self.initiated_by,
            self.end_date,
            self._id
        )

    def _get_registration(self):
        return Node.find_one(Q('embargo', 'eq', self))

    def _view_url_context(self, user_id, node):
        registration = node or self._get_registration()
        return {
            'node_id': registration._id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(Embargo, self)._email_template_context(user, node, is_authorizer, urls)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = settings.EMBARGO_PENDING_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'approval_link': approval_link,
                'project_name': registration.title,
                'disapproval_link': disapproval_link,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
                'approval_time_span': approval_time_span,
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'embargo_end_date': self.end_date,
            })
        return context

    def _on_reject(self, user):
        parent_registration = self._get_registration()
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_CANCELLED,
            params={
                'node': parent_registration.registered_from_id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user),
        )
        # Remove backref to parent project if embargo was for a new registration
        if not self.for_existing_registration:
            parent_registration.delete_registration_tree(save=True)
            parent_registration.registered_from = None
        # Delete parent registration if it was created at the time the embargo was initiated
        if not self.for_existing_registration:
            parent_registration.is_deleted = True
            parent_registration.save()

    def disapprove_embargo(self, user, token):
        """Cancels retraction if user is admin and token verifies."""
        self.reject(user, token)

    def _on_complete(self, user):
        super(Embargo, self)._on_complete(user)
        parent_registration = self._get_registration()
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_APPROVED,
            params={
                'node': parent_registration.registered_from_id,
                'registration': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(self.initiated_by),
        )
        self.save()

    def approve_embargo(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        self.approve(user, token)


class Retraction(EmailApprovableSanction):
    """
    Retraction object for public registrations.
    Externally (specifically in user-facing language) retractions should be referred to as "Withdrawals", i.e.
    "Retract Registration" -> "Withdraw Registration", "Retracted" -> "Withdrawn", etc.
    """

    DISPLAY_NAME = 'Retraction'
    SHORT_NAME = 'retraction'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_RETRACTION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user')
    justification = fields.StringField(default=None, validate=MaxLengthValidator(2048))

    def __repr__(self):
        parent_registration = None
        try:
            parent_registration = Node.find_one(Q('retraction', 'eq', self))
        except NoResultsFound:
            pass
        return ('<Retraction(parent_registration={0}, initiated_by={1}) '
                'with _id {2}>').format(
            parent_registration,
            self.initiated_by,
            self._id
        )

    def _view_url_context(self, user_id, node):
        registration = Node.find_one(Q('retraction', 'eq', self))
        return {
            'node_id': registration._id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            root_registration = Node.find_one(Q('retraction', 'eq', self))
            node_id = user_approval_state.get('node_id', root_registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = user_approval_state.get('rejection_token')
        if rejection_token:
            root_registration = Node.find_one(Q('retraction', 'eq', self))
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')
            approval_time_span = settings.RETRACTION_PENDING_TIME.days * 24

            registration = Node.find_one(Q('retraction', 'eq', self))

            return {
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'project_name': registration.title,
                'registration_link': registration_link,
                'approval_link': approval_link,
                'disapproval_link': disapproval_link,
                'approval_time_span': approval_time_span,
            }
        else:
            return {
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
            }

    def _on_reject(self, user):
        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_CANCELLED,
            params={
                'node': parent_registration.registered_from_id,
                'registration': parent_registration._id,
                'retraction_id': self._id,
            },
            auth=Auth(user),
            save=True,
        )

    def _on_complete(self, user):
        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_APPROVED,
            params={
                'node': parent_registration.registered_from_id,
                'retraction_id': self._id,
                'registration': parent_registration._id
            },
            auth=Auth(self.initiated_by),
        )
        # Remove any embargoes associated with the registration
        if parent_registration.embargo_end_date or parent_registration.is_pending_embargo:
            parent_registration.embargo.state = self.REJECTED
            parent_registration.registered_from.add_log(
                action=NodeLog.EMBARGO_CANCELLED,
                params={
                    'node': parent_registration.registered_from_id,
                    'registration': parent_registration._id,
                    'embargo_id': parent_registration.embargo._id,
                },
                auth=Auth(self.initiated_by),
            )
            parent_registration.embargo.save()
        # Ensure retracted registration is public
        # Pass auth=None because the registration initiator may not be
        # an admin on components (component admins had the opportunity
        # to disapprove the retraction by this point)
        for node in parent_registration.node_and_primary_descendants():
            node.set_privacy('public', auth=None, save=True, log=False)
            node.update_search()

    def approve_retraction(self, user, token):
        self.approve(user, token)

    def disapprove_retraction(self, user, token):
        self.reject(user, token)


class RegistrationApproval(PreregCallbackMixin, EmailApprovableSanction):

    DISPLAY_NAME = 'Approval'
    SHORT_NAME = 'registration_approval'

    AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_ADMIN
    NON_AUTHORIZER_NOTIFY_EMAIL_TEMPLATE = mails.PENDING_REGISTRATION_NON_ADMIN

    VIEW_URL_TEMPLATE = VIEW_PROJECT_URL_TEMPLATE
    APPROVE_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'
    REJECT_URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/?token={token}'

    initiated_by = fields.ForeignField('user')

    def _get_registration(self):
        return Node.find_one(Q('registration_approval', 'eq', self))

    def _view_url_context(self, user_id, node):
        user_approval_state = self.approval_state.get(user_id, {})
        node_id = user_approval_state.get('node_id', node._id)
        return {
            'node_id': node_id
        }

    def _approval_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        approval_token = user_approval_state.get('approval_token')
        if approval_token:
            registration = self._get_registration()
            node_id = user_approval_state.get('node_id', registration._id)
            return {
                'node_id': node_id,
                'token': approval_token,
            }

    def _rejection_url_context(self, user_id):
        user_approval_state = self.approval_state.get(user_id, {})
        rejection_token = self.approval_state.get(user_id, {}).get('rejection_token')
        if rejection_token:
            root_registration = self._get_registration()
            node_id = user_approval_state.get('node_id', root_registration._id)
            registration = Node.load(node_id)
            return {
                'node_id': registration.registered_from._id,
                'token': rejection_token,
            }

    def _email_template_context(self, user, node, is_authorizer=False, urls=None):
        context = super(RegistrationApproval, self)._email_template_context(user, node, is_authorizer, urls)
        urls = urls or self.stashed_urls.get(user._id, {})
        registration_link = urls.get('view', self._view_url(user._id, node))
        if is_authorizer:
            approval_link = urls.get('approve', '')
            disapproval_link = urls.get('reject', '')

            approval_time_span = settings.REGISTRATION_APPROVAL_TIME.days * 24

            registration = self._get_registration()

            context.update({
                'is_initiator': self.initiated_by == user,
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
                'approval_link': approval_link,
                'disapproval_link': disapproval_link,
                'approval_time_span': approval_time_span,
                'project_name': registration.title,
            })
        else:
            context.update({
                'initiated_by': self.initiated_by.fullname,
                'registration_link': registration_link,
            })
        return context

    def _add_success_logs(self, node, user):
        src = node.registered_from
        src.add_log(
            action=NodeLog.PROJECT_REGISTERED,
            params={
                'parent_node': src.parent_id,
                'node': src._primary_key,
                'registration': node._primary_key,
            },
            auth=Auth(user),
            save=False
        )
        src.save()

    def _on_complete(self, user):
        super(RegistrationApproval, self)._on_complete(user)
        self.state = Sanction.APPROVED
        register = self._get_registration()
        registered_from = register.registered_from
        # Pass auth=None because the registration initiator may not be
        # an admin on components (component admins had the opportunity
        # to disapprove the registration by this point)
        register.set_privacy('public', auth=None, log=False)
        for child in register.get_descendants_recursive(lambda n: n.primary):
            child.set_privacy('public', auth=None, log=False)
        # Accounts for system actions where no `User` performs the final approval
        auth = Auth(user) if user else None
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_APPROVED,
            params={
                'node': registered_from._id,
                'registration': register._id,
                'registration_approval_id': self._id,
            },
            auth=auth,
        )
        for node in register.root.node_and_primary_descendants():
            self._add_success_logs(node, user)
            node.update_search()  # update search if public

        self.save()

    def _on_reject(self, user):
        register = self._get_registration()
        registered_from = register.registered_from
        register.delete_registration_tree(save=True)
        registered_from.add_log(
            action=NodeLog.REGISTRATION_APPROVAL_CANCELLED,
            params={
                'node': registered_from._id,
                'registration': register._id,
                'registration_approval_id': self._id,
            },
            auth=Auth(user),
        )

class AlternativeCitation(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    name = fields.StringField(required=True, validate=MaxLengthValidator(256))
    text = fields.StringField(required=True, validate=MaxLengthValidator(2048))

    def to_json(self):
        return {
            "id": self._id,
            "name": self.name,
            "text": self.text
        }

class DraftRegistrationApproval(Sanction):

    mode = Sanction.ANY

    # Since draft registrations that require approval are not immediately registered,
    # meta stores registration_choice and embargo_end_date (when applicable)
    meta = fields.DictionaryField(default=dict)

    def _send_rejection_email(self, user, draft):
        schema = draft.registration_schema
        prereg_schema = prereg_utils.get_prereg_schema()

        if schema._id == prereg_schema._id:
            mails.send_mail(
                user.username,
                mails.PREREG_CHALLENGE_REJECTED,
                user=user,
                draft_url=draft.absolute_url
            )
        else:
            raise NotImplementedError(
                'TODO: add a generic email template for registration approvals'
            )

    def approve(self, user):
        if settings.PREREG_ADMIN_TAG not in user.system_tags:
            raise PermissionsError("This user does not have permission to approve this draft.")
        self.state = Sanction.APPROVED
        self._on_complete(user)

    def reject(self, user):
        if settings.PREREG_ADMIN_TAG not in user.system_tags:
            raise PermissionsError("This user does not have permission to approve this draft.")
        self.state = Sanction.REJECTED
        self._on_reject(user)

    def _on_complete(self, user):
        draft = DraftRegistration.find_one(
            Q('approval', 'eq', self)
        )
        auth = Auth(draft.initiator)
        registration = draft.register(
            auth=auth,
            save=True
        )
        registration_choice = self.meta['registration_choice']

        if registration_choice == 'immediate':
            sanction = functools.partial(registration.require_approval, draft.initiator)
        elif registration_choice == 'embargo':
            sanction = functools.partial(
                registration.embargo_registration,
                draft.initiator,
                parse_date(self.meta.get('embargo_end_date'), ignoretz=True)
            )
        else:
            raise ValueError("'registration_choice' must be either 'embargo' or 'immediate'")
        sanction(notify_initiator_on_complete=True)

    def _on_reject(self, user, *args, **kwargs):
        # clear out previous registration options
        self.meta = {}
        self.save()

        draft = DraftRegistration.find_one(
            Q('approval', 'eq', self)
        )
        self._send_rejection_email(draft.initiator, draft)


class DraftRegistration(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    URL_TEMPLATE = settings.DOMAIN + 'project/{node_id}/drafts/{draft_id}'

    datetime_initiated = fields.DateTimeField(auto_now_add=True)
    datetime_updated = fields.DateTimeField(auto_now=True)
    # Original Node a draft registration is associated with
    branched_from = fields.ForeignField('node', index=True)

    initiator = fields.ForeignField('user', index=True)

    # Dictionary field mapping question id to a question's comments and answer
    # {
    #   <qid>: {
    #     'comments': [{
    #       'user': {
    #         'id': <uid>,
    #         'name': <name>
    #       },
    #       value: <value>,
    #       lastModified: <datetime>
    #     }],
    #     'value': <value>
    #   }
    # }
    registration_metadata = fields.DictionaryField(default=dict)
    registration_schema = fields.ForeignField('metaschema')
    registered_node = fields.ForeignField('node', index=True)

    approval = fields.ForeignField('draftregistrationapproval', default=None)

    # Dictionary field mapping extra fields defined in the MetaSchema.schema to their
    # values. Defaults should be provided in the schema (e.g. 'paymentSent': false),
    # and these values are added to the DraftRegistration
    _metaschema_flags = fields.DictionaryField(default=None)
    # lazily set flags
    @property
    def flags(self):
        if not self._metaschema_flags:
            self._metaschema_flags = {}
        meta_schema = self.registration_schema
        if meta_schema:
            schema = meta_schema.schema
            flags = schema.get('flags', {})
            for flag, value in flags.iteritems():
                if flag not in self._metaschema_flags:
                    self._metaschema_flags[flag] = value
            self.save()
        return self._metaschema_flags

    @flags.setter
    def flags(self, flags):
        self._metaschema_flags.update(flags)

    notes = fields.StringField()

    @property
    def url(self):
        return self.URL_TEMPLATE.format(
            node_id=self.branched_from,
            draft_id=self._id
        )

    @property
    def absolute_url(self):
        return urlparse.urljoin(settings.DOMAIN, self.url)

    @property
    def requires_approval(self):
        return self.registration_schema.requires_approval

    @property
    def is_pending_review(self):
        return self.approval.is_pending_approval if (self.requires_approval and self.approval) else False

    @property
    def is_approved(self):
        if self.requires_approval:
            if not self.approval:
                return False
            else:
                return self.approval.is_approved
        else:
            return False

    @property
    def is_rejected(self):
        if self.requires_approval:
            if not self.approval:
                return False
            else:
                return self.approval.is_rejected
        else:
            return False

    @classmethod
    def create_from_node(cls, node, user, schema, data=None):
        draft = cls(
            initiator=user,
            branched_from=node,
            registration_schema=schema,
            registration_metadata=data or {},
        )
        draft.save()
        return draft

    def update_metadata(self, metadata):
        if self.is_approved:
            return []

        changes = []
        for question_id, value in metadata.iteritems():
            old_value = self.registration_metadata.get(question_id)
            if old_value:
                old_comments = {
                    comment['created']: comment
                    for comment in old_value.get('comments', [])
                }
                new_comments = {
                    comment['created']: comment
                    for comment in value.get('comments', [])
                }
                old_comments.update(new_comments)
                metadata[question_id]['comments'] = sorted(
                    old_comments.values(),
                    key=lambda c: c['created']
                )
                if old_value.get('value') != value.get('value'):
                    changes.append(question_id)
            else:
                changes.append(question_id)
        self.registration_metadata.update(metadata)
        return changes

    def submit_for_review(self, initiated_by, meta, save=False):
        approval = DraftRegistrationApproval(
            initiated_by=initiated_by,
            meta=meta
        )
        approval.save()
        self.approval = approval
        if save:
            self.save()

    def register(self, auth, save=False):
        node = self.branched_from

        # Create the registration
        register = node.register_node(
            schema=self.registration_schema,
            auth=auth,
            data=self.registration_metadata
        )
        self.registered_node = register
        if save:
            self.save()
        return register

    def approve(self, user):
        self.approval.approve(user)
        self.approval.save()

    def reject(self, user):
        self.approval.reject(user)
        self.approval.save()
