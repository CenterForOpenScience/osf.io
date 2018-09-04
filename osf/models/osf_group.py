from django.db import models
from guardian.shortcuts import assign_perm, remove_perm, get_perms
from framework.exceptions import PermissionsError

from osf.models import base
from osf.models.mixins import GuardianMixin
from osf.models.user import OSFUser
from osf.utils.permissions import ADMIN
from osf.utils import sanitize

MEMBER = 'member'
MANAGER = 'manager'

# TODO Add logging for OSFGroup actions
# TODO Add unregistered member/manager
# TODO Send email to member when added to group
# TODO OSFGroups should either have a guid or a longer _id


class OSFGroup(GuardianMixin, base.BaseModel):
    """
    OSFGroup model.  When an OSFGroup is created, a manager and member Django group are created.
    Managers belong to both manager and member groups.  Members belong to member group only.

    The OSFGroup's Django member group is given permissions to nodes.
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
            ('member_group', 'Has group membership'),
            ('manage_group', 'Can manage group membership'),
        )

    @property
    def manager_group(self):
        return self.get_group(MANAGER)

    @property
    def member_group(self):
        return self.get_group(MEMBER)

    @property
    def managers(self):
        return self.manager_group.user_set.all()

    @property
    def members(self):
        return self.member_group.user_set.all()

    def _require_manager_permission(self, auth=None):
        if auth and not self.has_permission(auth.user, 'manage'):
            raise PermissionsError('Must be a group manager to modify group membership.')

    def _enforce_one_manager(self, user):
        if len(self.managers) == 1 and self.managers[0] == user:
            raise ValueError('Group must have at least one manager')

    def send_member_email(self, user, permission, auth=None):
        pass

    def belongs_to_osfgroup(self, user):
        return user in self.members

    def make_member(self, user, auth=None):
        """Add member or downgrade manager to member

        :param user: OSFUser object, intended member
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        adding_member = not self.belongs_to_osfgroup(user)
        self.member_group.user_set.add(user)
        if self.has_permission(user, 'manage'):
            self._enforce_one_manager(user)
            self.manager_group.user_set.remove(user)

        if adding_member:
            self.send_member_email(user, MEMBER, auth)

    def make_manager(self, user, auth=None):
        """Add manager or upgrade member to manager

        :param user: OSFUser object, intended manager
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        adding_member = not self.belongs_to_osfgroup(user)
        self.manager_group.user_set.add(user)
        self.member_group.user_set.add(user)

        if adding_member:
            self.send_member_email(user, MANAGER, auth)

    def remove_member(self, user, auth=None):
        """Remove member

        :param user: OSFUser object, member to remove
        :param auth: Auth object
        """
        if not (auth and user == auth.user):
            self._require_manager_permission(auth)

        if user in self.managers:
            raise ValueError('Cannot remove manager using this method.')
        self.member_group.user_set.remove(user)

    def remove_manager(self, user, auth=None):
        """Remove manager

        :param user: OSFUser object, manager to remove
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        self._enforce_one_manager(user)
        self.manager_group.user_set.remove(user)
        self.remove_member(user)

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
        self.name = new_name

    def add_group_to_node(self, node, permission='write', auth=None):
        """Gives the OSF Group permissions to the node.  Called from node model.

        :param obj AbstractNode
        :param str Highest permission to grant, 'read', 'write', or 'admin'
        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        for perm in node.groups[permission]:
            assign_perm(perm, self.member_group, node)

    def update_group_permissions_to_node(self, node, permission='write', auth=None):
        """Updates the OSF Group permissions to the node.  Called from node model.

        :param obj AbstractNode
        :param str Highest permission to grant, 'read', 'write', or 'admin'
        :param auth: Auth object
        """
        to_remove = set(get_perms(self.member_group, node)).difference(node.groups[permission])
        for perm in to_remove:
            remove_perm(perm, self.member_group, node)
        for perm in node.groups[permission]:
            assign_perm(perm, self.member_group, node)

    def remove_group_from_node(self, node):
        """Removes the OSFGroup from the node. Called from node model.

        :param obj AbstractNode
        """
        # Just removes all permissions to the node, if they exist
        for perm in node.groups[ADMIN]:
            remove_perm(perm, self.member_group, node)

    def has_permission(self, user, permission):
        if not user:
            return False
        has_permission = user.has_perm('{}_group'.format(permission), self)
        return has_permission

    def remove_group(self, auth=None):
        """Removes the OSFGroup and associated manager and member django groups

        :param auth: Auth object
        """
        self._require_manager_permission(auth)
        self.member_group.delete()
        self.manager_group.delete()
        self.delete()

    def save(self, *args, **kwargs):
        first_save = not bool(self.pk)
        ret = super(OSFGroup, self).save(*args, **kwargs)

        if first_save:
            self.update_group_permissions()
            self.make_manager(self.creator)
        return ret
