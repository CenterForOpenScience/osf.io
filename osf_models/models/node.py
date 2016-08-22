import logging
import urlparse

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from keen import scoped_keys
from osf_models.models.identifiers import IdentifierMixin
from typedmodels.models import TypedModel

# OSF imports
from framework import status
from website.exceptions import UserNotAffiliatedError, NodeStateError
from website.util.permissions import (
    expand_permissions,
    DEFAULT_CONTRIBUTOR_PERMISSIONS,
    READ,
    WRITE,
    ADMIN
)
from website import settings
from framework.sentry import log_exception
from framework.exceptions import PermissionsError
from website.project import signals as project_signals

from osf_models.apps import AppConfig as app_config
from osf_models.models.nodelog import NodeLog
from osf_models.models.contributor import Contributor, RecentlyAddedContributor
from osf_models.models.mixins import Loggable, Taggable, AddonModelMixin
from osf_models.models.user import OSFUser
from osf_models.models.validators import validate_title
from osf_models.utils.auth import Auth, get_user
from osf_models.utils.base import api_v2_url
from osf_models.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf_models.modm_compat import Q

from .base import BaseModel, GuidMixin

logger = logging.getLogger(__name__)

class AbstractNode(TypedModel, AddonModelMixin, IdentifierMixin, Taggable, Loggable, GuidMixin, BaseModel):
    """
    All things that inherit from AbstractNode will appear in
    the same table and will be differentiated by the `type` column.
    """

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

    affiliated_institutions = models.ManyToManyField('Institution', related_name='nodes')
    # alternative_citations = models.ManyToManyField(AlternativeCitation)
    category = models.CharField(max_length=255,
                                choices=CATEGORY_MAP.items(),
                                blank=True,
                                default='')
    # Dictionary field mapping user id to a list of nodes in node.nodes which the user has subscriptions for
    # {<User.id>: [<Node._id>, <Node2._id>, ...] }
    # TODO: Can this be a reference instead of data?
    child_node_subscriptions = DateTimeAwareJSONField(default=dict, blank=True)
    contributors = models.ManyToManyField(OSFUser,
                                          through=Contributor,
                                          related_name='nodes')
    creator = models.ForeignKey(OSFUser,
                                db_index=True,
                                related_name='created',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)
    # TODO: Uncomment auto_* attributes after migration is complete
    date_created = models.DateTimeField(default=timezone.now)  # auto_now_add=True)
    date_modified = models.DateTimeField(db_index=True, null=True, blank=True)  # auto_now=True)
    deleted_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    file_guid_to_share_uuids = DateTimeAwareJSONField(default=dict, blank=True)
    forked_date = models.DateTimeField(db_index=True, null=True, blank=True)
    forked_from = models.ForeignKey('self',
                                    related_name='forks',
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    is_fork = models.BooleanField(default=False, db_index=True)
    is_public = models.BooleanField(default=False, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    node_license = models.ForeignKey('NodeLicenseRecord', related_name='nodes',
                                     on_delete=models.SET_NULL, null=True, blank=True)
    parent_node = models.ForeignKey('self',
                                    related_name='nodes',
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    # permissions = Permissions are now on contributors
    piwik_site_id = models.IntegerField(null=True, blank=True)
    public_comments = models.BooleanField(default=True)
    primary_institution = models.ForeignKey(
        'Institution',
        related_name='primary_nodes',
        null=True, blank=True)
    root = models.ForeignKey('self',
                             related_name='absolute_parent',
                             on_delete=models.SET_NULL,
                             null=True, blank=True)
    suspended = models.BooleanField(default=False, db_index=True)

    # The node (if any) used as a template for this node's creation
    template_node = models.ForeignKey('self',
                                      related_name='templated_from',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True)
    title = models.TextField(
        validators=[validate_title]
    )  # this should be a charfield but data from mongo didn't fit in 255
    # TODO why is this here if it's empty
    users_watching_node = models.ManyToManyField(OSFUser, related_name='watching')
    wiki_pages_current = DateTimeAwareJSONField(default=dict, blank=True)
    wiki_pages_versions = DateTimeAwareJSONField(default=dict, blank=True)
    # Dictionary field mapping node wiki page to sharejs private uuid.
    # {<page_name>: <sharejs_id>}
    wiki_private_uuids = DateTimeAwareJSONField(default=dict, blank=True)

    def __init__(self, *args, **kwargs):
        self._parent = kwargs.pop('parent', None)
        super(AbstractNode, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'{} : ({})'.format(self.title, self._id)

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
        return urlparse.urljoin(app_config.domain, self.url)

    @property
    def deep_url(self):
        return '/project/{}/'.format(self._primary_key)

    def update_search(self):
        from website import search
        try:
            search.search.update_node(self, bulk=False, async=True)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    def add_affiliated_intitution(self, inst, user, save=False, log=True):
        if not user.is_affiliated_with_institution(inst):
            raise UserNotAffiliatedError('User is not affiliated with {}'.format(inst.name))
        if inst not in self.affiliated_institutions:
            self.affiliated_institutions.add(inst)
        if log:
            from website.project.model import NodeLog

            self.add_log(
                action=NodeLog.AFFLILIATED_INSTITUTION_ADDED,
                params={
                    'node': self._primary_key,
                    'institution': {
                        'id': inst._id,
                        'name': inst.name
                    }
                },
                auth=Auth(user)
            )

    def can_view(self, auth):
        if auth and getattr(auth.private_link, 'anonymous', False):
            return self._id in auth.private_link.nodes

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

    @property
    def comment_level(self):
        if self.public_comments:
            return 'public'
        else:
            return 'private'

    @comment_level.setter
    def comment_level(self, value):
        if value == 'public':
            self.public_comments = True
        elif value == 'private':
            self.public_comments = False
        else:
            raise ValidationError(
                'comment_level must be either `public` or `private`')

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def get_permissions(self, user):
        contrib = user.contributor_set.get(node=self)
        perm = []
        if contrib.read:
            perm.append(READ)
        if contrib.write:
            perm.append(WRITE)
        if contrib.admin:
            perm.append(ADMIN)
        return perm

    def has_permission(self, user, permission):
        try:
            contrib = user.contributor_set.get(node=self)
        except Contributor.DoesNotExist:
            return False
        else:
            return getattr(contrib, permission, False)

    def add_permission(self, user, permission, save=False):
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

    @property
    def is_retracted(self):
        # TODO This property will need to recurse up the node hierarchy to check if any this
        # node's parents are retracted.
        # Same with is_pending_registration, etc. -- @sloria
        return False

    @property
    def nodes_pointer(self):
        return []

    @property
    def url(self):
        return '/{}/'.format(self._id)

    @property
    def parent_id(self):
        if self.parent_node:
            return self.parent_node._id
        return None

    # visible_contributor_ids was moved to this property
    @property
    def visible_contributor_ids(self):
        return self.contributor_set.filter(visible=True).values_list('user___guid__guid', flat=True)

    @property
    def system_tags(self):
        """The system tags associated with this node. This currently returns a list of string
        names for the tags, for compatibility with v1. Eventually, we can just return the
        QuerySet.
        """
        return self.tags.filter(system=True).values_list('name', flat=True)

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

            # TODO: Uncomment when NotificationSubscription is implemented
            # if self._id:
            #     project_signals.contributor_added.send(self, contributor=contributor, auth=auth)

            return True

        # Permissions must be overridden if changed when contributor is
        # added to parent he/she is already on a child of.
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
        contributor = OSFUser.create_unregistered(fullname=fullname, email=email)

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
            contributor.add_unclaimed_record(node=self, referrer=auth.user,
                given_name=fullname, email=email)
            contributor.save()

        self.add_contributor(
            contributor, permissions=permissions, auth=auth,
            log=True, save=False,
        )
        self.save()
        return contributor

    @classmethod
    def find_for_user(cls, user, subquery=None):
        combined_query = Q('contributors', 'eq', user)
        if subquery is not None:
            combined_query = combined_query & subquery
        return cls.find(combined_query)

    def can_comment(self, auth):
        if self.comment_level == 'public':
            return auth.logged_in and (
                self.is_public or
                (auth.user and self.has_permission(auth.user, 'read'))
            )
        return self.is_contributor(auth.user)

    def set_privacy(self, permissions, auth=None, log=True, save=True, meeting_creation=False):
        """Set the permissions for this node. Also, based on meeting_creation, queues
        an email to user about abilities of public projects.

        :param permissions: A string, either 'public' or 'private'
        :param auth: All the auth information including user, API key.
        :param bool log: Whether to add a NodeLog for the privacy change.
        :param bool meeting_creation: Whether this was created due to a meetings email.
        """
        if auth and not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Must be an admin to change privacy settings.')
        if permissions == 'public' and not self.is_public:
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

    def generate_keenio_read_key(self):
        return scoped_keys.encrypt(settings.KEEN['public']['master_key'], options={
            'filters': [{
                'property_name': 'node.id',
                'operator': 'eq',
                'property_value': str(self._id)
            }],
            'allowed_operations': ['read']
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

    def find_readable_antecedent(self, auth):
        """ Returns first antecendant node readable by <user>.
        """
        next_parent = self.parent_node
        while next_parent:
            if next_parent.can_view(auth):
                return next_parent
            next_parent = next_parent.parent_node


class Node(AbstractNode):
    """
    Concrete Node class: Instance of AbstractNode(TypedModel). All things that inherit
    from AbstractNode will appear in the same table and will be differentiated by the `type` column.

    FYI: Behaviors common between Registration and Node should be on the parent class.
    """
    @property
    def is_collection(self):
        """Compat with v1."""
        return False

@receiver(post_save, sender=Node)
def add_creator_as_contributor(sender, instance, created, **kwargs):
    if created:
        Contributor.objects.create(
            user=instance.creator,
            node=instance,
            visible=True,
            read=True,
            write=True,
            admin=True
        )

@receiver(pre_save, sender=Node)
def set_parent(sender, instance, *args, **kwargs):
    if getattr(instance, '_parent', None):
        instance.parent_node = instance._parent

class Collection(GuidMixin, BaseModel):
    # TODO: Uncomment auto_* attributes after migration is complete
    date_created = models.DateTimeField(null=False, default=timezone.now)  # auto_now_add=True)
    date_modified = models.DateTimeField(null=True, blank=True,
                                         db_index=True)  # auto_now=True)
    is_bookmark_collection = models.BooleanField(default=False, db_index=True)
    nodes = models.ManyToManyField('Node', related_name='children')
    title = models.TextField(
        validators=[validate_title]
    )  # this should be a charfield but data from mongo didn't fit in 255
    user = models.ForeignKey('OSFUser', null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='collections')

    @property
    def nodes_pointer(self):
        return self.nodes.filter(primary=False)

    @property
    def is_collection(self):
        """
        Just to keep compatibility with previous code.
        :return:
        """
        return True
