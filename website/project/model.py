# -*- coding: utf-8 -*-
import os
import re
import urllib
import logging
import datetime
import urlparse
from collections import OrderedDict
import warnings

import pytz
from flask import request
from django.core.urlresolvers import reverse
from HTMLParser import HTMLParser

from modularodm import Q
from modularodm import fields
from modularodm.validators import MaxLengthValidator
from modularodm.exceptions import ValidationTypeError
from modularodm.exceptions import ValidationValueError

from api.base.utils import absolute_reverse
from framework import status
from framework.mongo import ObjectId
from framework.mongo import StoredObject
from framework.addons import AddonModelMixin
from framework.auth import get_user, User, Auth
from framework.auth import signals as auth_signals
from framework.exceptions import PermissionsError
from framework.guid.model import GuidStoredObject
from framework.auth.utils import privacy_info_handle
from framework.analytics import tasks as piwik_tasks
from framework.mongo.utils import to_mongo, to_mongo_key, unique_on
from framework.analytics import (
    get_basic_counters, increment_user_activity_counters
)
from framework.sentry import log_exception
from framework.transactions.context import TokuTransaction
from framework.utils import iso8601format

from website import language, settings, security
from website.util import web_url_for
from website.util import api_url_for
from website.exceptions import (
    NodeStateError, InvalidRetractionApprovalToken,
    InvalidRetractionDisapprovalToken, InvalidEmbargoApprovalToken,
    InvalidEmbargoDisapprovalToken,
)
from website.citations.utils import datetime_to_csl
from website.identifiers.model import IdentifierMixin
from website.util.permissions import expand_permissions
from website.util.permissions import CREATOR_PERMISSIONS
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.util.permissions import DEFAULT_CONTRIBUTOR_PERMISSIONS
from website.project import signals as project_signals

html_parser = HTMLParser()

logger = logging.getLogger(__name__)


def has_anonymous_link(node, auth):
    """check if the node is anonymous to the user

    :param Node node: Node which the user wants to visit
    :param str link: any view-only link in the current url
    :return bool anonymous: Whether the node is anonymous to the user or not
    """
    view_only_link = auth.private_key or request.args.get('view_only', '').strip('/')
    if not view_only_link:
        return False
    if node.is_public:
        return False
    return any(
        link.anonymous
        for link in node.private_links_active
        if link.key == view_only_link
    )

class MetaSchema(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))
    name = fields.StringField()
    schema = fields.DictionaryField()
    category = fields.StringField()

    # Version of the Knockout metadata renderer to use (e.g. if data binds
    # change)
    metadata_version = fields.IntegerField()
    # Version of the schema to use (e.g. if questions, responses change)
    schema_version = fields.IntegerField()


def ensure_schemas(clear=True):
    """Import meta-data schemas from JSON to database, optionally clearing
    database first.

    :param clear: Clear schema database before import
    """
    if clear:
        try:
            MetaSchema.remove()
        except AttributeError:
            if not settings.DEBUG_MODE:
                raise
    for schema in OSF_META_SCHEMAS:
        try:
            MetaSchema.find_one(
                Q('name', 'eq', schema['name']) &
                Q('schema_version', 'eq', schema['schema_version'])
            )
        except:
            schema['name'] = schema['name'].replace(' ', '_')
            schema_obj = MetaSchema(**schema)
            schema_obj.save()


class MetaData(GuidStoredObject):

    _id = fields.StringField(primary=True)

    target = fields.AbstractForeignField(backref='metadata')
    data = fields.DictionaryField()

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_modified = fields.DateTimeField(auto_now=datetime.datetime.utcnow)


def validate_comment_reports(value, *args, **kwargs):
    for key, val in value.iteritems():
        if not User.load(key):
            raise ValidationValueError('Keys must be user IDs')
        if not isinstance(val, dict):
            raise ValidationTypeError('Values must be dictionaries')
        if 'category' not in val or 'text' not in val:
            raise ValidationValueError(
                'Values must include `category` and `text` keys'
            )


class Comment(GuidStoredObject):

    _id = fields.StringField(primary=True)

    user = fields.ForeignField('user', required=True, backref='commented')
    node = fields.ForeignField('node', required=True, backref='comment_owner')
    target = fields.AbstractForeignField(required=True, backref='commented')

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    date_modified = fields.DateTimeField(auto_now=datetime.datetime.utcnow)
    modified = fields.BooleanField()

    is_deleted = fields.BooleanField(default=False)
    content = fields.StringField()

    # Dictionary field mapping user IDs to dictionaries of report details:
    # {
    #   'icpnw': {'category': 'hate', 'message': 'offensive'},
    #   'cdi38': {'category': 'spam', 'message': 'godwins law'},
    # }
    reports = fields.DictionaryField(validate=validate_comment_reports)

    @classmethod
    def create(cls, auth, **kwargs):
        comment = cls(**kwargs)
        comment.save()

        comment.node.add_log(
            NodeLog.COMMENT_ADDED,
            {
                'project': comment.node.parent_id,
                'node': comment.node._id,
                'user': comment.user._id,
                'comment': comment._id,
            },
            auth=auth,
            save=False,
        )

        comment.node.save()

        return comment

    def edit(self, content, auth, save=False):
        self.content = content
        self.modified = True
        self.node.add_log(
            NodeLog.COMMENT_UPDATED,
            {
                'project': self.node.parent_id,
                'node': self.node._id,
                'user': self.user._id,
                'comment': self._id,
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()

    def delete(self, auth, save=False):
        self.is_deleted = True
        self.node.add_log(
            NodeLog.COMMENT_REMOVED,
            {
                'project': self.node.parent_id,
                'node': self.node._id,
                'user': self.user._id,
                'comment': self._id,
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()

    def undelete(self, auth, save=False):
        self.is_deleted = False
        self.node.add_log(
            NodeLog.COMMENT_ADDED,
            {
                'project': self.node.parent_id,
                'node': self.node._id,
                'user': self.user._id,
                'comment': self._id,
            },
            auth=auth,
            save=False,
        )
        if save:
            self.save()

    def report_abuse(self, user, save=False, **kwargs):
        """Report that a comment is abuse.

        :param User user: User submitting the report
        :param bool save: Save changes
        :param dict kwargs: Report details
        :raises: ValueError if the user submitting abuse is the same as the
            user who posted the comment
        """
        if user == self.user:
            raise ValueError
        self.reports[user._id] = kwargs
        if save:
            self.save()

    def unreport_abuse(self, user, save=False):
        """Revoke report of abuse.

        :param User user: User who submitted the report
        :param bool save: Save changes
        :raises: ValueError if user has not reported comment as abuse
        """
        try:
            self.reports.pop(user._id)
        except KeyError:
            raise ValueError('User has not reported comment as abuse')

        if save:
            self.save()


@unique_on(['params.node', '_id'])
class NodeLog(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    date = fields.DateTimeField(default=datetime.datetime.utcnow, index=True)
    action = fields.StringField(index=True)
    params = fields.DictionaryField()
    should_hide = fields.BooleanField(default=False)

    was_connected_to = fields.ForeignField('node', list=True)

    user = fields.ForeignField('user', backref='created')
    foreign_user = fields.StringField()

    DATE_FORMAT = '%m/%d/%Y %H:%M UTC'

    # Log action constants
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

    CONTRIB_ADDED = 'contributor_added'
    CONTRIB_REMOVED = 'contributor_removed'
    CONTRIB_REORDERED = 'contributors_reordered'

    PERMISSIONS_UPDATED = 'permissions_updated'

    MADE_PRIVATE = 'made_private'
    MADE_PUBLIC = 'made_public'

    TAG_ADDED = 'tag_added'
    TAG_REMOVED = 'tag_removed'

    EDITED_TITLE = 'edit_title'
    EDITED_DESCRIPTION = 'edit_description'

    UPDATED_FIELDS = 'updated_fields'

    FILE_MOVED = 'addon_file_moved'
    FILE_COPIED = 'addon_file_copied'

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

    def __repr__(self):
        return ('<NodeLog({self.action!r}, params={self.params!r}) '
                'with id {self._id!r}>').format(self=self)

    @property
    def node(self):
        """Return the :class:`Node` associated with this log."""
        return (
            Node.load(self.params.get('node')) or
            Node.load(self.params.get('project'))
        )

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

    def resolve_node(self, node):
        """A single `NodeLog` record may be attached to multiple `Node` records
        (parents, forks, registrations, etc.), so the node that the log refers
        to may not be the same as the node the user is viewing. Use
        `resolve_node` to determine the relevant node to use for permission
        checks.

        :param Node node: Node being viewed
        """
        if self.node == node or self.node in node.nodes:
            return self.node
        if node.is_fork_of(self.node) or node.is_registration_of(self.node):
            return node
        for child in node.nodes:
            if child.is_fork_of(self.node) or node.is_registration_of(self.node):
                return child
        return False

    def can_view(self, node, auth):
        node_to_check = self.resolve_node(node)
        if node_to_check:
            return node_to_check.can_view(auth)
        return False

    def _render_log_contributor(self, contributor, anonymous=False):
        user = User.load(contributor)
        if not user:
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


class Tag(StoredObject):

    _id = fields.StringField(primary=True, validate=MaxLengthValidator(128))

    def __repr__(self):
        return '<Tag() with id {self._id!r}>'.format(self=self)

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
    node = fields.ForeignField('node', backref='_pointed')

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
        """Delegate attribute access to the node being pointed to.
        """
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

class Node(GuidStoredObject, AddonModelMixin, IdentifierMixin):

    #: Whether this is a pointer or not
    primary = True

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
    }

    # Maps category identifier => Human-readable representation for use in
    # titles, menus, etc.
    # Use an OrderedDict so that menu items show in the correct order
    CATEGORY_MAP = OrderedDict([
        ('', 'Uncategorized'),
        ('project', 'Project'),
        ('hypothesis', 'Hypothesis'),
        ('methods and measures', 'Methods and Measures'),
        ('procedure', 'Procedure'),
        ('instrumentation', 'Instrumentation'),
        ('data', 'Data'),
        ('analysis', 'Analysis'),
        ('communication', 'Communication'),
        ('other', 'Other'),
    ])

    WRITABLE_WHITELIST = [
        'title',
        'description',
        'category',
    ]

    _id = fields.StringField(primary=True)

    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow, index=True)

    # Privacy
    is_public = fields.BooleanField(default=False, index=True)

    # User mappings
    permissions = fields.DictionaryField()
    visible_contributor_ids = fields.StringField(list=True)

    # Project Organization
    is_dashboard = fields.BooleanField(default=False, index=True)
    is_folder = fields.BooleanField(default=False, index=True)

    # Expanded: Dictionary field mapping user IDs to expand state of this node:
    # {
    #   'icpnw': True,
    #   'cdi38': False,
    # }
    expanded = fields.DictionaryField(default={}, validate=validate_user)

    is_deleted = fields.BooleanField(default=False, index=True)
    deleted_date = fields.DateTimeField(index=True)

    is_registration = fields.BooleanField(default=False, index=True)
    registered_date = fields.DateTimeField(index=True)
    registered_user = fields.ForeignField('user', backref='registered')
    registered_schema = fields.ForeignField('metaschema', backref='registered')
    registered_meta = fields.DictionaryField()
    retraction = fields.ForeignField('retraction')
    embargo = fields.ForeignField('embargo')

    is_fork = fields.BooleanField(default=False, index=True)
    forked_date = fields.DateTimeField(index=True)

    title = fields.StringField(validate=validate_title)
    description = fields.StringField()
    category = fields.StringField(validate=validate_category, index=True)

    # One of 'public', 'private'
    # TODO: Add validator
    comment_level = fields.StringField(default='private')

    wiki_pages_current = fields.DictionaryField()
    wiki_pages_versions = fields.DictionaryField()
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = fields.DictionaryField()
    file_guid_to_share_uuids = fields.DictionaryField()

    creator = fields.ForeignField('user', backref='created')
    contributors = fields.ForeignField('user', list=True, backref='contributed')
    users_watching_node = fields.ForeignField('user', list=True, backref='watched')

    logs = fields.ForeignField('nodelog', list=True, backref='logged')
    tags = fields.ForeignField('tag', list=True, backref='tagged')

    # Tags for internal use
    system_tags = fields.StringField(list=True)

    nodes = fields.AbstractForeignField(list=True, backref='parent')
    forked_from = fields.ForeignField('node', backref='forked', index=True)
    registered_from = fields.ForeignField('node', backref='registrations', index=True)

    # The node (if any) used as a template for this node's creation
    template_node = fields.ForeignField('node', backref='template_node', index=True)

    piwik_site_id = fields.StringField()

    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    child_node_subscriptions = fields.DictionaryField(default=dict)

    _meta = {
        'optimistic': True,
    }

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)

        if kwargs.get('_is_loaded', False):
            return

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

    @property
    def category_display(self):
        """The human-readable representation of this node's category."""
        return self.CATEGORY_MAP[self.category]

    @property
    def is_retracted(self):
        if self.retraction is None and self.parent_node:
            return self.parent_node.is_retracted
        return getattr(self.retraction, 'is_retracted', False)

    @property
    def pending_retraction(self):
        if self.retraction is None and self.parent_node:
            return self.parent_node.pending_retraction
        return getattr(self.retraction, 'pending_retraction', False)

    @property
    def embargo_end_date(self):
        if self.embargo is None and self.parent_node:
            return self.parent_node.embargo_end_date
        return getattr(self.embargo, 'embargo_end_date', False)

    @property
    def pending_embargo(self):
        if self.embargo is None and self.parent_node:
            return self.parent_node.pending_embargo
        return getattr(self.embargo, 'pending_embargo', False)

    @property
    def pending_registration(self):
        if self.embargo is None and self.parent_node:
            return self.parent_node.pending_registration
        return getattr(self.embargo, 'pending_registration', False)

    @property
    def private_links(self):
        return self.privatelink__shared

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
        if not auth and not self.is_public:
            return False

        return (
            self.is_public or
            (auth.user and self.has_permission(auth.user, 'read')) or
            auth.private_key in self.private_link_keys_active or
            self.is_admin_parent(auth.user)
        )

    def is_expanded(self, user=None):
        """Return if a user is has expanded the folder in the dashboard view.
        Must specify one of (`auth`, `user`).

        :param User user: User object to check
        :returns: Boolean if the folder is expanded.
        """
        if user._id in self.expanded:
            return self.expanded[user._id]
        else:
            return False

    def expand(self, user=None):
        self.expanded[user._id] = True
        self.save()

    def collapse(self, user=None):
        self.expanded[user._id] = False
        self.save()

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
        return list(self.node__forked.find(Q('is_deleted', 'eq', False) &
                                           Q('is_registration', 'ne', True)))

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
            logger.warn('User is ``None``.')
            return False
        if permission in self.permissions.get(user._id, []):
            return True
        if permission == 'read' and check_parent:
            return self.is_admin_parent(user)
        return False

    def can_read_children(self, user):
        """Checks if the given user has read permissions on any child nodes
            that are not registrations or deleted
        """
        if self.has_permission(user, 'read'):
            return True

        for node in self.nodes:
            if not node.primary or node.is_deleted:
                continue

            if node.can_read_children(user):
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
                raise ValueError(
                    'Must have at least one visible contributor'
                )
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

    def update(self, fields, auth=None, save=True):
        if self.is_registration:
            raise NodeUpdateError(reason="Registered content cannot be updated")
        values = {}
        for key, value in fields.iteritems():
            if key not in self.WRITABLE_WHITELIST:
                continue
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
                    values[key] = {
                        'old': getattr(self, key),
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
        self.add_log(NodeLog.UPDATED_FIELDS,
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

        if first_save and self.is_dashboard:
            existing_dashboards = self.creator.node__contributed.find(
                Q('is_dashboard', 'eq', True)
            )
            if existing_dashboards.count() > 0:
                raise NodeStateError("Only one dashboard allowed per user.")

        is_original = not self.is_registration and not self.is_fork
        if 'suppress_log' in kwargs.keys():
            suppress_log = kwargs['suppress_log']
            del kwargs['suppress_log']
        else:
            suppress_log = False

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

        # Only update Solr if at least one stored field has changed, and if
        # public or privacy setting has changed
        need_update = bool(self.SOLR_UPDATE_FIELDS.intersection(saved_fields))
        if not self.is_public:
            if first_save or 'is_public' not in saved_fields:
                need_update = False
        if self.is_folder or self.archiving:
            need_update = False
        if need_update:
            self.update_search()

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
        new.add_contributor(contributor=auth.user, permissions=CREATOR_PERMISSIONS, log=False, save=False)
        new.template_node = self
        new.is_fork = False
        new.is_registration = False
        new.piwik_site_id = None

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
            if x.can_view(auth)
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

        # If a folder, prevent more than one pointer to that folder. This will prevent infinite loops on the Dashboard.
        # Also, no pointers to the dashboard project, which could cause loops as well.
        already_pointed = node.pointed
        if node.is_folder and len(already_pointed) > 0:
            raise ValueError(
                'Pointer to folder {0} already exists. Only one pointer to any given folder allowed'.format(node._id)
            )
        if node.is_dashboard:
            raise ValueError(
                'Pointer to dashboard ({0}) not allowed.'.format(node._id)
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
            raise ValueError

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

    def get_aggregate_logs_queryset(self, auth):
        ids = [self._id] + [n._id
                            for n in self.get_descendants_recursive()
                            if n.can_view(auth)]
        query = Q('__backrefs.logged.node.logs', 'in', ids)
        return NodeLog.find(query).sort('-_id')

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
        return getattr(self, '_pointed', [])

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
            if not folders and pointer_node.is_folder:
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
        return list(reversed(self.logs)[:n])

    @property
    def date_modified(self):
        '''The most recent datetime when this node was modified, based on
        the logs.
        '''
        try:
            return self.logs[-1].date
        except IndexError:
            return self.date_created

    def set_title(self, title, auth, save=False):
        """Set the title of this Node and log it.

        :param str title: The new title.
        :param auth: All the auth information including user, API key.
        """
        #Called so validation does not have to wait until save.
        validate_title(title)

        original_title = self.title
        self.title = title
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
        self.description = description
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
            search.search.update_node(self)
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

    def remove_node(self, auth, date=None):
        """Marks a node as deleted.

        TODO: Call a hook on addons
        Adds a log to the parent node if applicable

        :param auth: an instance of :class:`Auth`.
        :param date: Date node was removed
        :type date: `datetime.datetime` or `None`
        """
        # TODO: rename "date" param - it's shadowing a global

        if self.is_dashboard:
            raise NodeStateError("Dashboards may not be deleted.")

        if not self.can_edit(auth):
            raise PermissionsError('{0!r} does not have permission to modify this {1}'.format(auth.user, self.category or 'node'))

        #if this is a folder, remove all the folders that this is pointing at.
        if self.is_folder:
            for pointed in self.nodes_pointer:
                if pointed.node.is_folder:
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

        forked.logs = self.logs
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

        # Forks default to private status
        forked.is_public = False

        # Clear permissions before adding users
        forked.permissions = {}
        forked.visible_contributor_ids = []

        forked.add_contributor(
            contributor=user,
            permissions=CREATOR_PERMISSIONS,
            log=False,
            save=False
        )

        forked.add_log(
            action=NodeLog.NODE_FORKED,
            params={
                'parent_node': original.parent_id,
                'node': original._primary_key,
                'registration': forked._primary_key,
            },
            auth=auth,
            log_date=when,
            save=False,
        )

        forked.save()
        # After fork callback
        for addon in original.get_addons():
            _, message = addon.after_fork(original, forked, user)
            if message:
                status.push_status_message(message, kind='info', trust=True)

        return forked

    def register_node(self, schema, auth, template, data, parent=None):
        """Make a frozen copy of a node.

        :param schema: Schema object
        :param auth: All the auth information including user, API key.
        :param template: Template name
        :param data: Form data
        :param parent Node: parent registration of registration to be created
        """
        # NOTE: Admins can register child nodes even if they don't have write access them
        if not self.can_edit(auth=auth) and not self.is_admin_parent(user=auth.user):
            raise PermissionsError(
                'User {} does not have permission '
                'to register this node'.format(auth.user._id)
            )
        if self.is_folder:
            raise NodeStateError("Folders may not be registered")

        template = urllib.unquote_plus(template)
        template = to_mongo(template)

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
        registered.registered_schema = schema
        registered.registered_from = original
        if not registered.registered_meta:
            registered.registered_meta = {}
        registered.registered_meta[template] = data

        registered.contributors = self.contributors
        registered.forked_from = self.forked_from
        registered.creator = self.creator
        registered.logs = self.logs
        registered.tags = self.tags
        registered.piwik_site_id = None

        registered.save()

        if parent:
            registered.parent_node = parent

        # After register callback
        for addon in original.get_addons():
            _, message = addon.after_register(original, registered, auth.user)
            if message:
                status.push_status_message(message, kind='info', trust=False)

        for node_contained in original.nodes:
            if not node_contained.is_deleted:
                child_registration = node_contained.register_node(
                    schema, auth, template, data, parent=registered
                )
                if child_registration and not child_registration.primary:
                    registered.nodes.append(child_registration)

        registered.save()

        if settings.ENABLE_ARCHIVER:
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

    def add_tag(self, tag, auth, save=True):
        if tag not in self.tags:
            new_tag = Tag.load(tag)
            if not new_tag:
                new_tag = Tag(_id=tag)
            new_tag.save()
            self.tags.append(new_tag)
            self.add_log(
                action=NodeLog.TAG_ADDED,
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

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True):
        user = auth.user if auth else None
        params['node'] = params.get('node') or params.get('project')
        log = NodeLog(
            action=action,
            user=user,
            foreign_user=foreign_user,
            params=params,
        )
        if log_date:
            log.date = log_date
        log.save()
        self.logs.append(log)
        if save:
            self.save()
        if user:
            increment_user_activity_counters(user._primary_key, action, log.date)
        return log

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
        return absolute_reverse('nodes:node-detail', kwargs={'node_id': self._id})

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
    def csl(self):  # formats node information into CSL format for citation parsing
        """a dict in CSL-JSON schema

        For details on this schema, see:
            https://github.com/citation-style-language/schema#csl-json-schema
        """
        csl = {
            'id': self._id,
            'title': html_parser.unescape(self.title),
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
        return [
            x
            for x in self.node__template_node
            if not x.is_deleted
        ]

    @property
    def parent_node(self):
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

    @parent_node.setter
    def parent_node(self, parent):
        parent.nodes.append(self)
        parent.save()

    @property
    def root(self):
        if self.parent_node:
            return self.parent_node.root
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
    def registrations(self):
        return self.node__registrations.find(Q('archiving', 'eq', False))

    @property
    def watch_url(self):
        return os.path.join(self.api_url, "watch/")

    @property
    def parent_id(self):
        if self.node__parent:
            return self.node__parent[0]._primary_key
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
        # TODO: Move to validator or helper
        admins = [
            user for user in self.contributors
            if self.has_permission(user, 'admin')
            and user.is_registered
        ]
        if not admins:
            return False

        # Clear permissions for removed user
        self.permissions.pop(contributor._id, None)

        # After remove callback
        for addon in self.get_addons():
            message = addon.after_remove_contributor(self, contributor, auth)
            if message:
                status.push_status_message(message, kind='info', trust=True)

        if log:
            self.add_log(
                action=NodeLog.CONTRIB_REMOVED,
                params={
                    'project': self.parent_id,
                    'node': self._primary_key,
                    'contributor': contributor._id,
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
                self.set_visible(user, user_dict['visible'], auth=auth)
                users.append(user)
                user_ids.append(user_dict['id'])

            for user in self.contributors:
                if user._id in user_ids:
                    to_retain.append(user)
                else:
                    to_remove.append(user)

            # TODO: Move to validator or helper @jmcarp
            admins = [
                user for user in users
                if self.has_permission(user, 'admin')
                and user.is_registered
            ]
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

        #Permissions must be overridden if changed when contributor is added to parent he/she is already on a child of.
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

    def set_privacy(self, permissions, auth=None, log=True, save=True):
        """Set the permissions for this node.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        """
        if permissions == 'public' and not self.is_public:
            if self.is_registration:
                if self.pending_embargo:
                    raise NodeStateError("A registration with an unapproved embargo cannot be made public")
                if self.embargo_end_date and not self.pending_embargo:
                    self.embargo.state = Embargo.CANCELLED
                    self.embargo.save()
            self.is_public = True
        elif permissions == 'private' and self.is_public:
            if self.is_registration and not self.pending_embargo:
                raise NodeStateError("Public registrations must be retracted, not made private.")
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
        return True

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

        new_page = NodeWikiPage(
            page_name=name,
            version=version,
            user=auth.user,
            is_current=True,
            node=self,
            content=content
        )
        new_page.save()

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
            'title': html_parser.unescape(self.title),
            'path': self.path_above(auth),
            'api_url': self.api_url,
            'is_public': self.is_public,
            'is_registration': self.is_registration,
        }

    def _initiate_retraction(self, user, justification=None, save=False):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param justification: Justification, if given, for retraction
        """

        retraction = Retraction()
        retraction.initiated_by = user
        if justification:
            retraction.justification = justification
        retraction.state = Retraction.PENDING

        admins = [contrib for contrib in self.contributors if self.has_permission(contrib, 'admin') and contrib.is_active]

        approval_state = {}
        # Create approve/disapprove tokens
        for admin in admins:
            approval_state[admin._id] = {
                'approval_token': security.random_string(30),
                'disapproval_token': security.random_string(30),
                'has_approved': False
            }

        retraction.approval_state = approval_state
        # Retraction record needs to be saved to ensure the forward reference Node->Retraction
        if save:
            retraction.save()
        return retraction

    def retract_registration(self, user, justification=None, save=True):
        """Retract public registration. Instantiate new Retraction object
        and associate it with the respective registration.
        """

        if not self.is_registration or (not self.is_public and not (self.embargo_end_date or self.pending_embargo)):
            raise NodeStateError('Only public registrations or active embargoes may be retracted.')

        if self.root is not self:
            raise NodeStateError('Retraction of non-parent registrations is not permitted.')

        retraction = self._initiate_retraction(user, justification, save=True)
        self.registered_from.add_log(
            action=NodeLog.RETRACTION_INITIATED,
            params={
                'node': self._id,
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

    def _initiate_embargo(self, user, end_date, for_existing_registration=False, save=False):
        """Initiates the retraction process for a registration
        :param user: User who initiated the retraction
        :param end_date: Date when the registration should be made public
        """

        embargo = Embargo()
        embargo.initiated_by = user
        embargo.for_existing_registration = for_existing_registration
        # Convert Date to Datetime
        embargo.end_date = datetime.datetime.combine(end_date, datetime.datetime.min.time())

        admins = [contrib for contrib in self.contributors if self.has_permission(contrib, 'admin') and contrib.is_active]
        embargo.approval_state = {
            admin._id: {
                'approval_token': security.random_string(30),
                'disapproval_token': security.random_string(30),
                'has_approved': False
            } for admin in admins
        }
        if save:
            embargo.save()
        return embargo

    def embargo_registration(self, user, end_date, for_existing_registration=False):
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

        embargo = self._initiate_embargo(user, end_date, for_existing_registration=for_existing_registration, save=True)

        self.registered_from.add_log(
            action=NodeLog.EMBARGO_INITIATED,
            params={
                'node': self._id,
                'embargo_id': embargo._id,
            },
            auth=Auth(user),
            save=True,
        )
        # Embargo record needs to be saved to ensure the forward reference Node->Embargo
        self.embargo = embargo
        if self.is_public:
            self.set_privacy('private', Auth(user))


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
    node = fields.ForeignField('Node', backref='watched')
    digest = fields.BooleanField(default=False)
    immediate = fields.BooleanField(default=False)

    def __repr__(self):
        return '<WatchConfig(node="{self.node}")>'.format(self=self)


class PrivateLink(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    date_created = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    key = fields.StringField(required=True)
    name = fields.StringField()
    is_deleted = fields.BooleanField(default=False)
    anonymous = fields.BooleanField(default=False)

    nodes = fields.ForeignField('node', list=True, backref='shared')
    creator = fields.ForeignField('user', backref='created')

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
            "name": self.name,
            "creator": {'fullname': self.creator.fullname, 'url': self.creator.profile_url},
            "nodes": [{'title': x.title, 'url': x.url, 'scale': str(self.node_scale(x)) + 'px', 'category': x.category}
                      for x in self.nodes if not x.is_deleted],
            "anonymous": self.anonymous
        }


def validate_retraction_state(value):
    acceptable_states = [Retraction.PENDING, Retraction.RETRACTED, Retraction.CANCELLED]
    if value not in acceptable_states:
        raise ValidationValueError('Invalid retraction state assignment.')

    return True


class Retraction(StoredObject):
    """Retraction object for public registrations."""

    PENDING = 'pending'
    RETRACTED = 'retracted'
    CANCELLED = 'cancelled'

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    justification = fields.StringField(default=None, validate=MaxLengthValidator(2048))
    initiation_date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    initiated_by = fields.ForeignField('user', backref='retracted')
    # Expanded: Dictionary field mapping admin IDs their approval status and relevant tokens:
    # {
    #   'b3k97': {
    #     'has_approved': False,
    #     'approval_token': 'Cru7wj1Puf7DENUPFPnXSwa1rf3xPN',
    #     'disapproval_token': 'UotzClTFOic2PYxHDStby94bCQMwJy'}
    # }
    approval_state = fields.DictionaryField()
    # One of 'pending', 'retracted', or 'cancelled'
    state = fields.StringField(default='pending', validate=validate_retraction_state)

    def __repr__(self):
        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        return ('<Retraction(parent_registration={0}, initiated_by={1}) '
                'with _id {2}>').format(
            parent_registration,
            self.initiated_by,
            self._id
        )

    @property
    def is_retracted(self):
        return self.state == self.RETRACTED

    @property
    def pending_retraction(self):
        return self.state == self.PENDING

    def disapprove_retraction(self, user, token):
        """Cancels retraction if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['disapproval_token'] != token:
                raise InvalidRetractionDisapprovalToken('Invalid retraction disapproval token provided.')
        except KeyError:
            raise PermissionsError('User must be an admin to disapprove retraction of a registration.')

        self.state = self.CANCELLED
        parent_registration = Node.find_one(Q('retraction', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.RETRACTION_CANCELLED,
            params={
                'node': parent_registration._id,
                'retraction_id': self._id,
            },
            auth=Auth(user),
            save=True,
        )

    def approve_retraction(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['approval_token'] != token:
                raise InvalidRetractionApprovalToken('Invalid retraction approval token provided.')
        except KeyError:
            raise PermissionsError('User must be an admin to disapprove retraction of a registration.')

        self.approval_state[user._id]['has_approved'] = True
        if all(val['has_approved'] for val in self.approval_state.values()):
            self.state = self.RETRACTED

            parent_registration = Node.find_one(Q('retraction', 'eq', self))
            parent_registration.registered_from.add_log(
                action=NodeLog.RETRACTION_APPROVED,
                params={
                    'node': parent_registration._id,
                    'retraction_id': self._id,
                },
                auth=Auth(user),
            )
            # Remove any embargoes associated with the registration
            if parent_registration.embargo_end_date or parent_registration.pending_embargo:
                parent_registration.embargo.state = self.CANCELLED
                parent_registration.registered_from.add_log(
                    action=NodeLog.EMBARGO_CANCELLED,
                    params={
                        'node': parent_registration._id,
                        'embargo_id': parent_registration.embargo._id,
                    },
                    auth=Auth(user),
                )
                parent_registration.embargo.save()
            # Ensure retracted registration is public
            if not parent_registration.is_public:
                parent_registration.set_privacy('public')
            parent_registration.update_search()
            # Retraction status is inherited from the root project, so we
            # need to recursively update search for every descendant node
            # so that retracted subrojects/components don't appear in search
            for node in parent_registration.get_descendants_recursive():
                node.update_search()


def validate_embargo_state(value):
    acceptable_states = [
        Embargo.UNAPPROVED, Embargo.ACTIVE, Embargo.CANCELLED, Embargo.COMPLETED
    ]
    if value not in acceptable_states:
        raise ValidationValueError('Invalid embargo state assignment.')
    return True


class Embargo(StoredObject):
    """Embargo object for registrations waiting to go public."""

    UNAPPROVED = 'unapproved'
    ACTIVE = 'active'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    initiation_date = fields.DateTimeField(auto_now_add=datetime.datetime.utcnow)
    initiated_by = fields.ForeignField('user', backref='embargoed')
    end_date = fields.DateTimeField()
    # Expanded: Dictionary field mapping admin IDs their approval status and relevant tokens:
    # {
    #   'b3k97': {
    #     'has_approved': False,
    #     'approval_token': 'Pew7wj1Puf7DENUPFPnXSwa1rf3xPN',
    #     'disapproval_token': 'TwozClTFOic2PYxHDStby94bCQMwJy'}
    # }
    approval_state = fields.DictionaryField()
    # One of 'unapproved', 'active', 'cancelled', or 'completed
    state = fields.StringField(default='unapproved', validate=validate_embargo_state)
    for_existing_registration = fields.BooleanField(default=False)

    def __repr__(self):
        parent_registration = Node.find_one(Q('embargo', 'eq', self))
        return ('<Embargo(parent_registration={0}, initiated_by={1}, '
                'end_date={2}) with _id {3}>').format(
            parent_registration,
            self.initiated_by,
            self.end_date,
            self._id
        )

    @property
    def embargo_end_date(self):
        if self.state == Embargo.ACTIVE:
            return self.end_date
        return False

    @property
    def pending_embargo(self):
        return self.state == Embargo.UNAPPROVED

    # NOTE(hrybacki): Old, private registrations are grandfathered and do not
    # require to be made public or embargoed. This field differentiates them
    # from new registrations entering into an embargo field which should not
    # show up in any search related fields.
    @property
    def pending_registration(self):
        return not self.for_existing_registration and self.pending_embargo

    def disapprove_embargo(self, user, token):
        """Cancels retraction if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['disapproval_token'] != token:
                raise InvalidEmbargoDisapprovalToken('Invalid embargo disapproval token provided.')
        except KeyError:
            raise PermissionsError('User must be an admin to disapprove embargoing of a registration.')

        self.state = Embargo.CANCELLED
        parent_registration = Node.find_one(Q('embargo', 'eq', self))
        parent_registration.registered_from.add_log(
            action=NodeLog.EMBARGO_CANCELLED,
            params={
                'node': parent_registration._id,
                'embargo_id': self._id,
            },
            auth=Auth(user),
        )
        # Remove backref to parent project if embargo was for a new registration
        if not self.for_existing_registration:
            parent_registration.registered_from = None
        # Delete parent registration if it was created at the time the embargo was initiated
        if not self.for_existing_registration:
            parent_registration.is_deleted = True
            parent_registration.save()

    def approve_embargo(self, user, token):
        """Add user to approval list if user is admin and token verifies."""
        try:
            if self.approval_state[user._id]['approval_token'] != token:
                raise InvalidEmbargoApprovalToken('Invalid embargo approval token provided.')
        except KeyError:
            raise PermissionsError('User must be an admin to disapprove embargoing of a registration.')

        self.approval_state[user._id]['has_approved'] = True
        if all(val['has_approved'] for val in self.approval_state.values()):
            self.state = Embargo.ACTIVE
            parent_registration = Node.find_one(Q('embargo', 'eq', self))
            parent_registration.registered_from.add_log(
                action=NodeLog.EMBARGO_APPROVED,
                params={
                    'node': parent_registration._id,
                    'embargo_id': self._id,
                },
                auth=Auth(user),
            )
