import logging
import functools
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm, get_perms, get_objects_for_group, get_group_perms
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from framework.exceptions import PermissionsError
from framework.auth.core import get_user, Auth
from framework.sentry import log_exception
from osf.exceptions import BlacklistedEmailError
from osf.models import base
from osf.models.mixins import GuardianMixin, Loggable
from osf.models import Node, OSFUser, NodeLog
from osf.models.osf_grouplog import OSFGroupLog
from osf.models.validators import validate_email
from osf.utils.permissions import ADMIN, READ_NODE, WRITE, MANAGER, MEMBER, MANAGE, reduce_permissions
from osf.utils import sanitize
from website.project import signals as project_signals
from website.osf_groups import signals as group_signals
from website.util import api_v2_url

logger = logging.getLogger(__name__)


class OSFGroup(GuardianMixin, Loggable, base.ObjectIDMixin, base.BaseModel):
    """
    OSFGroup model.  When an OSFGroup is created, a manager and member Django group are created.
    Managers belong to both manager and member groups.  Members belong to the member group only.

    The OSFGroup's Django member group is given permissions to nodes, so all OSFGroup members
    get the same permission to the node.
    """

    name = models.TextField(blank=False)
    creator = models.ForeignKey(OSFUser,
                                db_index=True,
                                related_name='osfgroups_created',
                                on_delete=models.SET_NULL,
                                null=True, blank=True)

    groups = {
        'member': ('member_group',),
        'manager': ('manage_group',),
    }
    group_format = 'osfgroup_{self.id}_{group}'

    def __unicode__(self):
        return 'OSFGroup_{}_{}'.format(self.id, self.name)

    class Meta:
        permissions = (
            ('view_group', 'Can view group details'),
            ('member_group', 'Has group membership'),
            ('manage_group', 'Can manage group membership'),
        )

    @property
    def _primary_key(self):
        return self._id

    @property
    def manager_group(self):
        """
        OSFGroup's Django manager group object
        """
        return self.get_group(MANAGER)

    @property
    def member_group(self):
        """
        OSFGroup's Django member group object
        """
        return self.get_group(MEMBER)

    @property
    def managers(self):
        # All users that belong to the OSF Group's manager group
        return self.manager_group.user_set.all()

    @property
    def members(self):
        # All members/managers belonging to this OSFGroup -
        # the member group has both members and managers
        return self.member_group.user_set.all()

    @property
    def members_only(self):
        # Users that are truly members-only and not managers
        return self.members.exclude(id__in=self.managers)

    @property
    def nodes(self):
        """
        Returns nodes that the OSF group has permission to
        """
        return get_objects_for_group(self.member_group, READ_NODE, Node)

    @property
    def absolute_api_v2_url(self):
        path = '/groups/{}/'.format(self._id)
        return api_v2_url(path)

    @property
    def url(self):
        # TODO - front end hasn't been set up
        return '/{}/'.format(self._primary_key)

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    def is_member(self, user):
        # Checking group membership instead of permissions, because unregistered
        # members have no perms
        return user in self.members

    def is_manager(self, user):
        # Checking group membership instead of permissions, because unregistered
        # members have no perms
        return user in self.managers

    def _require_manager_permission(self, auth=None):
        if auth and not self.has_permission(auth.user, MANAGE):
            raise PermissionsError('Must be a group manager to modify group membership.')

    def _disabled_user_check(self, user):
        if user.is_disabled:
            raise ValueError('Deactivated users cannot be added to OSF Groups.')

    def _enforce_one_manager(self, user):
        # Group must have at least one registered manager
        if (len(self.managers) == 1 and self.managers[0] == user) or not self.managers.filter(is_registered=True).exclude(id=user.id):
            raise ValueError('Group must have at least one manager.')

    def _get_node_group_perms(self, node, permission):
        """
        Gets expanded permissions for a node.  The expanded permissions can be used
        to add to the member group.

        Raises error if permission is invalid.
        """
        permissions = node.groups.get(permission)
        if not permissions:
            raise ValueError('{} is not a valid permission.'.format(permission))
        return permissions

    def send_member_email(self, user, permission, auth=None):
        group_signals.member_added.send(self, user=user, permission=permission, auth=auth)

    def make_member(self, user, auth=None):
        """Add member or downgrade manager to member

        :param user: OSFUser object, intended member
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        self._disabled_user_check(user)
        adding_member = not self.is_member(user)
        if user in self.members_only:
            return False

        self.member_group.user_set.add(user)
        if self.is_manager(user):
            self._enforce_one_manager(user)
            self.manager_group.user_set.remove(user)
            self.add_role_updated_log(user, MEMBER, auth)
        else:
            self.add_log(
                OSFGroupLog.MEMBER_ADDED,
                params={
                    'group': self._id,
                    'user': user._id,
                },
                auth=auth)
        self.update_search()

        if adding_member:
            self.send_member_email(user, MEMBER, auth)

    def make_manager(self, user, auth=None):
        """Add manager or upgrade member to manager

        :param user: OSFUser object, intended manager
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        self._disabled_user_check(user)
        adding_member = not self.is_member(user)
        if self.is_manager(user):
            return False

        if not self.is_member(user):
            self.add_log(
                OSFGroupLog.MANAGER_ADDED,
                params={
                    'group': self._id,
                    'user': user._id,
                },
                auth=auth)

        else:
            self.add_role_updated_log(user, MANAGER, auth)
        self.manager_group.user_set.add(user)
        self.member_group.user_set.add(user)
        self.update_search()

        if adding_member:
            self.send_member_email(user, MANAGER, auth)

    def add_unregistered_member(self, fullname, email, auth, role=MEMBER):
        """Add unregistered member or manager to OSFGroup

        :param fullname: string, user fullname
        :param email: email, user email
        :param auth: Auth object
        :param role: string, "member" or "manager", default is member
        """
        OSFUser = apps.get_model('osf.OSFUser')

        try:
            validate_email(email)
        except BlacklistedEmailError:
            raise ValidationError('Email address domain is blacklisted.')

        user = get_user(email=email)
        if user:
            if user.is_registered or self.is_member(user):
                raise ValueError('User already exists.')
        else:
            user = OSFUser.create_unregistered(fullname=fullname, email=email)
        user.add_unclaimed_record(self, referrer=auth.user, given_name=fullname, email=email)
        user.save()

        if role == MANAGER:
            self.make_manager(user, auth=auth)
        else:
            self.make_member(user, auth=auth)

        return user

    def replace_contributor(self, old, new):
        """
        Replacing unregistered member with a verified user

        Using "replace_contributor" language to mimic Node model, so this can be called in
        the same views using to claim accounts on nodes.
        """
        if not self.is_member(old):
            return False

        # Remove unclaimed record for the group
        if self._id in old.unclaimed_records:
            del old.unclaimed_records[self._id]
            old.save()

        # For the manager and member Django group attached to the OSFGroup,
        # add the new user to the group, and remove the old.  This
        # will give the new user the appropriate permissions to the OSFGroup
        for group_name in self.groups.keys():
            if self.get_group(group_name).user_set.filter(id=old.id).exists():
                self.get_group(group_name).user_set.remove(old)
                self.get_group(group_name).user_set.add(new)

        self.update_search()
        return True

    def remove_member(self, user, auth=None):
        """Remove member or manager

        :param user: OSFUser object, member/manager to remove
        :param auth: Auth object
        """
        if not (auth and user == auth.user):
            self._require_manager_permission(auth)

        if not self.is_member(user):
            return False
        self._enforce_one_manager(user)
        self.manager_group.user_set.remove(user)
        self.member_group.user_set.remove(user)

        self.add_log(
            OSFGroupLog.MEMBER_REMOVED,
            params={
                'group': self._id,
                'user': user._id,
            },
            auth=auth)

        self.update_search()

        for node in self.nodes:
            project_signals.contributor_removed.send(node, user=user)
            node.disconnect_addons(user, auth)

    def set_group_name(self, name, auth=None):
        """Set the name of the group.

        :param str new Name: The new osf group name
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        new_name = sanitize.strip_html(name)
        # Title hasn't changed after sanitzation, bail out
        if self.name == new_name:
            return False
        old_name = self.name
        self.name = new_name

        self.add_log(
            OSFGroupLog.EDITED_NAME,
            params={
                'group': self._id,
                'name_original': old_name
            },
            auth=auth)
        self.update_search()
        for node in self.nodes:
            node.update_search()

    def add_group_to_node(self, node, permission=WRITE, auth=None):
        """Gives the OSF Group permissions to the node.  Called from node model.

        :param obj Node
        :param str Highest permission to grant, 'read', 'write', or 'admin'
        :param auth: Auth object
        """
        self._require_manager_permission(auth)

        current_perm = self.get_permission_to_node(node)
        if current_perm:
            if current_perm == permission:
                return False
            # If group already has perms to node, update permissions instead
            return self.update_group_permissions_to_node(node, permission, auth)

        permissions = self._get_node_group_perms(node, permission)
        for perm in permissions:
            assign_perm(perm, self.member_group, node)

        params = {
            'group': self._id,
            'node': node._id,
            'permission': permission
        }

        self.add_log(
            OSFGroupLog.NODE_CONNECTED,
            params=params,
            auth=auth)

        self.add_corresponding_node_log(node, NodeLog.GROUP_ADDED, params, auth)
        node.update_search()

        for user in self.members:
            group_signals.group_added_to_node.send(self, node=node, user=user, permission=permission, auth=auth)

    def update_group_permissions_to_node(self, node, permission=WRITE, auth=None):
        """Updates the OSF Group permissions to the node.  Called from node model.

        :param obj Node
        :param str Highest permission to grant, 'read', 'write', or 'admin'
        :param auth: Auth object
        """
        if self.get_permission_to_node(node) == permission:
            return False
        permissions = self._get_node_group_perms(node, permission)
        to_remove = set(get_perms(self.member_group, node)).difference(permissions)
        for perm in to_remove:
            remove_perm(perm, self.member_group, node)
        for perm in permissions:
            assign_perm(perm, self.member_group, node)
        params = {
            'group': self._id,
            'node': node._id,
            'permission': permission
        }
        self.add_log(
            OSFGroupLog.NODE_PERMS_UPDATED,
            params=params,
            auth=auth
        )

        self.add_corresponding_node_log(node, NodeLog.GROUP_UPDATED, params, auth)

    def remove_group_from_node(self, node, auth):
        """Removes the OSFGroup from the node. Called from node model.

        :param obj Node
        """
        if not self.get_permission_to_node(node):
            return False
        for perm in node.groups[ADMIN]:
            remove_perm(perm, self.member_group, node)
        params = {
            'group': self._id,
            'node': node._id,
        }
        self.add_log(
            OSFGroupLog.NODE_DISCONNECTED,
            params=params,
            auth=auth)

        self.add_corresponding_node_log(node, NodeLog.GROUP_REMOVED, params, auth)
        node.update_search()

        for user in self.members:
            node.disconnect_addons(user, auth)
            project_signals.contributor_removed.send(node, user=user)

    def get_permission_to_node(self, node):
        """
        Returns the permission this OSF group has to the given node

        :param node: Node object
        """
        perms = get_group_perms(self.member_group, node)
        return reduce_permissions(perms) if perms else None

    def has_permission(self, user, permission):
        """Returns whether the user has the given permission to the OSFGroup
        :param user: Auth object
        :param role: member/manange permission
        :return Boolean
        """
        if not user or user.is_anonymous:
            return False

        # Using get_group_perms to get permissions that are inferred through
        # group membership - not inherited from superuser status
        return '{}_{}'.format(permission, 'group') in get_group_perms(user, self)

    def remove_group(self, auth=None):
        """Removes the OSFGroup and associated manager and member django groups
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        group_id = self._id
        members = list(self.members.values_list('id', flat=True))
        nodes = self.nodes

        self.member_group.delete()
        self.manager_group.delete()
        self.delete()
        self.update_search(deleted_id=group_id)

        for user in OSFUser.objects.filter(id__in=members):
            for node in nodes:
                node.disconnect_addons(user, auth)
                params = {
                    'group': group_id,
                    'node': node._id,
                }
                self.add_corresponding_node_log(node, NodeLog.GROUP_REMOVED, params, auth)
                project_signals.contributor_removed.send(node, user=user)
                node.update_search()

    def save(self, *args, **kwargs):
        first_save = not bool(self.pk)
        ret = super(OSFGroup, self).save(*args, **kwargs)
        if first_save:
            self.update_group_permissions()
            self.make_manager(self.creator)

        return ret

    def add_role_updated_log(self, user, role, auth=None):
        """Creates a log when role changes
        :param auth: Auth object
        """
        self.add_log(
            OSFGroupLog.ROLE_UPDATED,
            params={
                'group': self._id,
                'new_role': role,
                'user': user._id,
            },
            auth=auth)

    def add_corresponding_node_log(self, node, action, params, auth):
        """ Used for logging OSFGroup-related action to nodes - for example,
        adding a group to a node.

        :param node: Node object
        :param action: string, Node log action
        :param params: dict, log params
        """
        node.add_log(
            action=action,
            params=params,
            auth=auth,
            save=True
        )

    def add_log(self, action, params, auth, log_date=None, save=True):
        """Create OSFGroupLog
        :param action: string, OSFGroup log action
        :param params: dict, log params
        """
        user = None
        if auth:
            user = auth.user

        log = OSFGroupLog(
            action=action, user=user,
            params=params, group=self
        )

        log.save()

        self._complete_add_log(log, action, user, save)
        return log

    def update_search(self, deleted_id=None):
        from website import search

        try:
            search.search.update_group(self, bulk=False, async_update=True, deleted_id=deleted_id)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()

    @classmethod
    def bulk_update_search(cls, groups, index=None):
        from website import search
        try:
            serialize = functools.partial(search.search.update_group, index=index, bulk=True, async_update=False)
            search.search.bulk_update_nodes(serialize, groups, index=index)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()


@receiver(post_save, sender=OSFGroup)
def add_project_created_log(sender, instance, created, **kwargs):
    if created:
        log_action = OSFGroupLog.GROUP_CREATED
        log_params = {
            'group': instance._id,
        }

        instance.add_log(
            log_action,
            params=log_params,
            auth=Auth(user=instance.creator),
            log_date=instance.created,
            save=True,
        )


class OSFGroupUserObjectPermission(UserObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - User models - we typically add object
    perms directly to Django groups instead of users, so this will be used infrequently
    """
    content_object = models.ForeignKey(OSFGroup, on_delete=models.CASCADE)


class OSFGroupGroupObjectPermission(GroupObjectPermissionBase):
    """
    Direct Foreign Key Table for guardian - Group models. Makes permission checks faster.

    This table gives a Django group a particular permission to an OSF Group.
    (Every time an OSFGroup is created, a Django member group, and Django manager group are created.
    The member group is given member perms, manager group has manager perms.)
    """
    content_object = models.ForeignKey(OSFGroup, on_delete=models.CASCADE)
