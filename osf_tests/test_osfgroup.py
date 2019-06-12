import mock
import pytest
import time
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from addons.github.tests import factories
from addons.osfstorage.models import OsfStorageFile
from framework.auth import Auth
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from framework.exceptions import PermissionsError
from osf.models import OSFGroup, Node, OSFUser, OSFGroupLog, NodeLog
from osf.utils.permissions import MANAGER, MEMBER, MANAGE, READ, WRITE, ADMIN
from website.notifications.utils import get_all_node_subscriptions
from website.osf_groups import signals as group_signals
from .factories import (
    NodeFactory,
    ProjectFactory,
    AuthUserFactory,
    OSFGroupFactory
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def manager():
    return AuthUserFactory()

@pytest.fixture()
def member():
    return AuthUserFactory()

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()

@pytest.fixture()
def user_three():
    return AuthUserFactory()

@pytest.fixture()
def auth(manager):
    return Auth(manager)

@pytest.fixture()
def project(manager):
    return ProjectFactory(creator=manager)

@pytest.fixture()
def osf_group(manager, member):
    osf_group = OSFGroupFactory(creator=manager)
    osf_group.make_member(member)
    return osf_group

class TestOSFGroup:

    def test_osf_group_creation(self, manager, member, user_two, fake):
        osf_group = OSFGroup.objects.create(name=fake.bs(), creator=manager)
        # OSFGroup creator given manage permissions
        assert osf_group.has_permission(manager, MANAGE) is True
        assert osf_group.has_permission(user_two, MANAGE) is False

        assert manager in osf_group.managers
        assert manager in osf_group.members
        assert manager not in osf_group.members_only

        user_two.is_superuser = True
        user_two.save()

        # Superusers don't have permission to group
        assert osf_group.has_permission(user_two, MEMBER) is False

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_make_manager(self, mock_send_mail, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(member))

        # manage permissions
        osf_group.make_manager(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, MANAGE) is True
        assert user_two in osf_group.managers
        assert user_two in osf_group.members
        assert mock_send_mail.call_count == 1

        # upgrade to manager
        osf_group.make_manager(member, Auth(manager))
        assert osf_group.has_permission(member, MANAGE) is True
        assert member in osf_group.managers
        assert member in osf_group.members
        # upgrading an existing member does not re-send an email
        assert mock_send_mail.call_count == 1

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_make_member(self, mock_send_mail, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(member))

        # manage permissions
        osf_group.make_member(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, MANAGE) is False
        assert user_two not in osf_group.managers
        assert user_two in osf_group.members
        assert mock_send_mail.call_count == 1

        # downgrade to member, sole manager
        with pytest.raises(ValueError):
            osf_group.make_member(manager, Auth(manager))

        # downgrade to member
        osf_group.make_manager(user_two, Auth(manager))
        assert user_two in osf_group.managers
        assert user_two in osf_group.members
        osf_group.make_member(user_two, Auth(manager))
        assert user_two not in osf_group.managers
        assert user_two in osf_group.members
        assert mock_send_mail.call_count == 1

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_add_unregistered_member(self, mock_send_mail, manager, member, osf_group, user_two):
        test_fullname = 'Test User'
        test_email = 'test_member@cos.io'
        test_manager_email = 'test_manager@cos.io'

        # Email already exists
        with pytest.raises(ValueError):
            osf_group.add_unregistered_member(test_fullname, user_two.username, auth=Auth(manager))

        # Test need manager perms to add
        with pytest.raises(PermissionsError):
            osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(member))

        # Add member
        osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(manager))
        assert mock_send_mail.call_count == 1
        unreg_user = OSFUser.objects.get(username=test_email)
        assert unreg_user in osf_group.members
        assert unreg_user not in osf_group.managers
        assert osf_group.has_permission(unreg_user, MEMBER) is True
        assert osf_group._id in unreg_user.unclaimed_records

        # Attempt to add unreg user as a member
        with pytest.raises(ValueError):
            osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(manager))

        # Add unregistered manager
        osf_group.add_unregistered_member(test_fullname, test_manager_email, auth=Auth(manager), role=MANAGER)
        assert mock_send_mail.call_count == 2
        unreg_manager = OSFUser.objects.get(username=test_manager_email)
        assert unreg_manager in osf_group.members
        assert unreg_manager in osf_group.managers
        assert osf_group.has_permission(unreg_manager, MEMBER) is True
        assert osf_group._id in unreg_manager.unclaimed_records

        # Add unregistered member with blacklisted email
        with pytest.raises(ValidationError):
            osf_group.add_unregistered_member(test_fullname, 'test@example.com', auth=Auth(manager), role=MANAGER)

    def test_remove_member(self, manager, member, user_three, osf_group):
        new_member = AuthUserFactory()
        osf_group.make_member(new_member)
        assert new_member not in osf_group.managers
        assert new_member in osf_group.members

        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_member, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_member, Auth(member))

        # manage permissions
        osf_group.remove_member(new_member, Auth(manager))
        assert new_member not in osf_group.managers
        assert new_member not in osf_group.members

        # Remove self - member can remove themselves
        osf_group.remove_member(member, Auth(member))
        assert member not in osf_group.managers
        assert member not in osf_group.members

    def test_remove_manager(self, manager, member, user_three, osf_group):
        new_manager = AuthUserFactory()
        osf_group.make_manager(new_manager)
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_manager, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.remove_member(new_manager, Auth(member))

        # manage permissions
        osf_group.remove_member(new_manager, Auth(manager))
        assert new_manager not in osf_group.managers
        assert new_manager not in osf_group.members

        # can't remove last manager
        with pytest.raises(ValueError):
            osf_group.remove_member(manager, Auth(manager))
        assert manager in osf_group.managers
        assert manager in osf_group.members

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_notify_group_member_email_does_not_send_before_throttle_expires(self, mock_send_mail, manager, osf_group):
        member = AuthUserFactory()
        assert member.member_added_email_records == {}
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager))
        assert mock_send_mail.call_count == 1

        record = member.member_added_email_records[osf_group._id]
        assert record is not None
        # 2nd call does not send email because throttle period has not expired
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager))
        assert member.member_added_email_records[osf_group._id] == record
        assert mock_send_mail.call_count == 1

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_notify_group_member_email_sends_after_throttle_expires(self, mock_send_mail, osf_group, member, manager):
        throttle = 0.5

        member = AuthUserFactory()
        assert member.member_added_email_records == {}
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager), throttle=throttle)
        assert mock_send_mail.call_count == 1

        time.sleep(1)  # throttle period expires
        # 2nd call does not send email because throttle period has not expired
        assert member.member_added_email_records[osf_group._id] is not None
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager), throttle=throttle)
        assert mock_send_mail.call_count == 2

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_notify_group_unregistered_member_throttle(self, mock_send_mail, osf_group, member, manager):
        throttle = 0.5

        member = AuthUserFactory()
        member.is_registered = False
        member.add_unclaimed_record(osf_group, referrer=manager, given_name='grapes mcgee', email='grapes@cos.io')
        member.save()
        assert member.member_added_email_records == {}
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager), throttle=throttle)
        assert mock_send_mail.call_count == 1

        assert member.member_added_email_records[osf_group._id] is not None
        # 2nd call does not send email because throttle period has not expired
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager))
        assert mock_send_mail.call_count == 1

        time.sleep(1)  # throttle period expires
        # 2nd call does not send email because throttle period has not expired
        assert member.member_added_email_records[osf_group._id] is not None
        group_signals.member_added.send(osf_group, user=member, permission=WRITE, auth=Auth(manager), throttle=throttle)
        assert mock_send_mail.call_count == 2

    def test_rename_osf_group(self, manager, member, user_two, osf_group):
        new_name = 'Platform Team'
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.set_group_name(new_name, Auth(user_two))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.set_group_name(new_name, Auth(member))

        # manage permissions
        osf_group.set_group_name(new_name, Auth(manager))
        osf_group.save()

        assert osf_group.name == new_name

    def test_remove_group(self, manager, member, osf_group):
        osf_group_name = osf_group.name
        manager_group_name = osf_group.manager_group.name
        member_group_name = osf_group.member_group.name

        osf_group.remove_group(Auth(manager))
        assert not OSFGroup.objects.filter(name=osf_group_name).exists()
        assert not Group.objects.filter(name=manager_group_name).exists()
        assert not Group.objects.filter(name=member_group_name).exists()

        assert manager_group_name not in manager.groups.values_list('name', flat=True)

    def test_remove_group_node_perms(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, ADMIN)
        assert project.has_permission(member, ADMIN) is True

        osf_group.remove_group(Auth(manager))

        assert project.has_permission(member, ADMIN) is False

    def test_user_groups_property(self, manager, member, osf_group):
        assert osf_group in manager.osf_groups
        assert osf_group in member.osf_groups

        other_group = OSFGroupFactory()

        assert other_group not in manager.osf_groups
        assert other_group not in member.osf_groups

    def test_user_group_roles(self, manager, member, user_three, osf_group):
        assert manager.group_role(osf_group) == MANAGER
        assert member.group_role(osf_group) == MEMBER
        assert user_three.group_role(osf_group) is None

    def test_replace_contributor(self, manager, member, osf_group):
        user = osf_group.add_unregistered_member('test_user', 'test@cos.io', auth=Auth(manager))
        assert user in osf_group.members
        assert user not in osf_group.managers
        assert (
            osf_group._id in
            user.unclaimed_records.keys()
        )
        osf_group.replace_contributor(user, member)
        assert user not in osf_group.members
        assert user not in osf_group.managers
        assert osf_group.has_permission(member, MEMBER) is True
        assert osf_group.has_permission(user, MEMBER) is False

        # test unclaimed_records is removed
        assert (
            osf_group._id not in
            user.unclaimed_records.keys()
        )

    def test_get_users_with_perm_osf_groups(self, project, manager, member, osf_group):
        # Explicitly added as a contributor
        read_users = project.get_users_with_perm(READ)
        write_users = project.get_users_with_perm(WRITE)
        admin_users = project.get_users_with_perm(ADMIN)
        assert len(project.get_users_with_perm(READ)) == 1
        assert len(project.get_users_with_perm(WRITE)) == 1
        assert len(project.get_users_with_perm(ADMIN)) == 1
        assert manager in read_users
        assert manager in write_users
        assert manager in admin_users

        # Added through osf groups
        project.add_osf_group(osf_group, WRITE)
        read_users = project.get_users_with_perm(READ)
        write_users = project.get_users_with_perm(WRITE)
        admin_users = project.get_users_with_perm(ADMIN)
        assert len(project.get_users_with_perm(READ)) == 2
        assert len(project.get_users_with_perm(WRITE)) == 2
        assert len(project.get_users_with_perm(ADMIN)) == 1
        assert member in read_users
        assert member in write_users
        assert member not in admin_users

    @pytest.mark.enable_quickfiles_creation
    def test_merge_users_transfers_group_membership(self, member, manager, osf_group):
        # merge member
        other_user = AuthUserFactory()
        other_user.merge_user(member)
        other_user.save()
        assert osf_group.is_member(other_user)

        # merge manager
        other_other_user = AuthUserFactory()
        other_other_user.merge_user(manager)
        other_other_user.save()
        assert osf_group.is_member(other_other_user)
        assert osf_group.has_permission(other_other_user, MANAGE)

    @pytest.mark.enable_quickfiles_creation
    def test_merge_users_already_group_manager(self, member, manager, osf_group):
        # merge users - both users have group membership - different roles
        manager.merge_user(member)
        manager.save()
        assert osf_group.has_permission(manager, MANAGE)
        assert osf_group.is_member(member) is False

    def test_osf_group_is_admin_parent(self, project, manager, member, osf_group, user_two, user_three):
        child = NodeFactory(parent=project, creator=manager)
        assert project.is_admin_parent(manager) is True
        assert project.is_admin_parent(member) is False

        project.add_contributor(user_two, WRITE, save=True)
        assert project.is_admin_parent(user_two) is False

        assert child.is_admin_parent(manager) is True
        child.add_contributor(user_two, ADMIN, save=True)
        assert child.is_admin_parent(user_two) is True

        assert child.is_admin_parent(user_three) is False
        osf_group.make_member(user_three)
        project.add_osf_group(osf_group, WRITE)
        assert child.is_admin_parent(user_three) is False

        project.update_osf_group(osf_group, ADMIN)
        assert child.is_admin_parent(user_three) is True
        assert child.is_admin_parent(user_three, include_group_admin=False) is False
        project.remove_osf_group(osf_group)

        child.add_osf_group(osf_group, WRITE)
        assert child.is_admin_parent(user_three) is False
        child.update_osf_group(osf_group, ADMIN)
        assert child.is_admin_parent(user_three) is True
        assert child.is_admin_parent(user_three, include_group_admin=False) is False


class TestNodeGroups:
    def test_node_contributors_and_group_members(self, manager, member, osf_group, project, user, user_two):
        assert project.contributors_and_group_members.count() == 1
        project.add_osf_group(osf_group, ADMIN)
        assert project.contributors_and_group_members.count() == 2
        project.add_contributor(user, WRITE)
        project.add_contributor(user_two, READ)
        project.save()
        assert project.contributors_and_group_members.count() == 4

    def test_add_osf_group_to_node_already_connected(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, ADMIN)
        assert project.has_permission(member, ADMIN) is True

        project.add_osf_group(osf_group, WRITE)
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is True

    def test_osf_group_nodes(self, manager, member, project, osf_group):
        nodes = osf_group.nodes
        assert len(nodes) == 0
        project.add_osf_group(osf_group, READ)
        assert project in osf_group.nodes

        project_two = ProjectFactory(creator=manager)
        project_two.add_osf_group(osf_group, WRITE)
        assert len(osf_group.nodes) == 2
        assert project_two in osf_group.nodes

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_add_osf_group_to_node(self, mock_send_mail, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, WRITE, auth=Auth(member))

        # Non-admin on project
        project.add_contributor(user_two, WRITE)
        project.save()
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, WRITE, auth=Auth(user_two))

        project.add_osf_group(osf_group, READ, auth=Auth(manager))
        assert mock_send_mail.call_count == 1
        # Manager was already a node admin
        assert project.has_permission(manager, ADMIN) is True
        assert project.has_permission(manager, WRITE) is True
        assert project.has_permission(manager, READ) is True

        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is False
        assert project.has_permission(member, READ) is True

        project.update_osf_group(osf_group, WRITE, auth=Auth(manager))
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        project.update_osf_group(osf_group, ADMIN, auth=Auth(manager))
        assert project.has_permission(member, ADMIN) is True
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        # project admin cannot add a group they are not a manager of
        other_group = OSFGroupFactory()
        with pytest.raises(PermissionsError):
            project.add_osf_group(other_group, ADMIN, auth=Auth(project.creator))

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_add_osf_group_to_node_emails_and_subscriptions(self, mock_send_mail, manager, member, user_two, osf_group, project):
        osf_group.make_member(user_two)

        # Manager is already a node contributor - already has subscriptions
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 0
        assert len(get_all_node_subscriptions(user_two, project)) == 0
        assert mock_send_mail.call_count == 1

        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        # Three members of group, but user adding group to node doesn't get email
        assert mock_send_mail.call_count == 3
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 2

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 0
        assert len(get_all_node_subscriptions(user_two, project)) == 0

        # Member is a contributor
        project.add_contributor(member, WRITE, save=True)
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 0

        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 2

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 0

        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 2

        # Don't unsubscribe member because they belong to a group that has perms
        project.remove_contributor(member, Auth(manager))
        assert len(get_all_node_subscriptions(manager, project)) == 2
        assert len(get_all_node_subscriptions(member, project)) == 2
        assert len(get_all_node_subscriptions(user_two, project)) == 2

    @mock.patch('website.osf_groups.views.mails.send_mail')
    def test_add_group_to_node_throttle(self, mock_send_mail, osf_group, manager, member, project):
        throttle = 100
        assert manager.group_connected_email_records == {}
        group_signals.group_added_to_node.send(osf_group, node=project, user=manager, permission=WRITE, auth=Auth(member), throttle=throttle)
        assert mock_send_mail.call_count == 1

        assert manager.group_connected_email_records[osf_group._id] is not None
        # 2nd call does not send email because throttle period has not expired
        group_signals.group_added_to_node.send(osf_group, node=project, user=manager, permission=WRITE, auth=Auth(member), throttle=throttle)
        assert mock_send_mail.call_count == 1

        throttle = 0.5

        time.sleep(1)  # throttle period expires
        # 2nd call does not send email because throttle period has not expired
        assert manager.group_connected_email_records[osf_group._id] is not None
        group_signals.group_added_to_node.send(osf_group, node=project, user=manager, permission=WRITE, auth=Auth(member), throttle=throttle)
        assert mock_send_mail.call_count == 2

    def test_add_osf_group_to_node_default_permission(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, auth=Auth(manager))

        assert project.has_permission(manager, ADMIN) is True
        assert project.has_permission(manager, WRITE) is True
        assert project.has_permission(manager, READ) is True

        # osf_group given write permissions by default
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

    def test_update_osf_group_node(self, manager, member, user_two, user_three, osf_group, project):
        project.add_osf_group(osf_group, ADMIN)

        assert project.has_permission(member, ADMIN) is True
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        project.update_osf_group(osf_group, READ)
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is False
        assert project.has_permission(member, READ) is True

        project.update_osf_group(osf_group, WRITE)
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        project.update_osf_group(osf_group, ADMIN)
        assert project.has_permission(member, ADMIN) is True
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        # Project admin who does not belong to the manager group can update group permissions
        project.add_contributor(user_two, ADMIN, save=True)
        project.update_osf_group(osf_group, READ, auth=Auth(user_two))
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is False
        assert project.has_permission(member, READ) is True

        # Project write contributor cannot update group permissions
        project.add_contributor(user_three, WRITE, save=True)
        with pytest.raises(PermissionsError):
            project.update_osf_group(osf_group, ADMIN, auth=Auth(user_three))
        assert project.has_permission(member, ADMIN) is False

    def test_remove_osf_group_from_node(self, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.remove_osf_group(osf_group, auth=Auth(member))

        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        assert project.has_permission(member, ADMIN) is True
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, READ) is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is False
        assert project.has_permission(member, READ) is False

        # Project admin who does not belong to the manager group can remove the group
        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        project.add_contributor(user_two, ADMIN)
        project.save()
        project.remove_osf_group(osf_group, auth=Auth(user_two))
        assert project.has_permission(member, ADMIN) is False
        assert project.has_permission(member, WRITE) is False
        assert project.has_permission(member, READ) is False

        # Manager who is not an admin can remove the group
        user_three = AuthUserFactory()
        osf_group.make_manager(user_three)
        project.add_osf_group(osf_group, WRITE)
        assert project.has_permission(user_three, ADMIN) is False
        assert project.has_permission(user_three, WRITE) is True
        assert project.has_permission(user_three, READ) is True
        project.remove_osf_group(osf_group, auth=Auth(user_three))
        assert project.has_permission(user_three, ADMIN) is False
        assert project.has_permission(user_three, WRITE) is False
        assert project.has_permission(user_three, READ) is False

    def test_node_groups_property(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, ADMIN, auth=Auth(manager))
        project.save()
        assert osf_group in project.osf_groups
        assert len(project.osf_groups) == 1

        group_two = OSFGroupFactory(creator=manager)
        project.add_osf_group(group_two, ADMIN, auth=Auth(manager))
        project.save()
        assert group_two in project.osf_groups
        assert len(project.osf_groups) == 2

    def test_get_osf_groups_with_perms_property(self, manager, member, osf_group, project):
        second_group = OSFGroupFactory(creator=manager)
        third_group = OSFGroupFactory(creator=manager)
        fourth_group = OSFGroupFactory(creator=manager)
        OSFGroupFactory(creator=manager)

        project.add_osf_group(osf_group, ADMIN)
        project.add_osf_group(second_group, WRITE)
        project.add_osf_group(third_group, WRITE)
        project.add_osf_group(fourth_group, READ)

        read_groups = project.get_osf_groups_with_perms(READ)
        assert len(read_groups) == 4

        write_groups = project.get_osf_groups_with_perms(WRITE)
        assert len(write_groups) == 3

        admin_groups = project.get_osf_groups_with_perms(ADMIN)
        assert len(admin_groups) == 1

        with pytest.raises(ValueError):
            project.get_osf_groups_with_perms('crazy')

    def test_osf_group_node_can_view(self, project, manager, member, osf_group):
        assert project.can_view(Auth(member)) is False
        project.add_osf_group(osf_group, READ)
        assert project.can_view(Auth(member)) is True
        assert project.can_edit(Auth(member)) is False

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, WRITE)
        assert project.can_view(Auth(member)) is True
        assert project.can_edit(Auth(member)) is True

        child = ProjectFactory(parent=project)
        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, ADMIN)
        # implicit OSF Group admin
        assert child.can_view(Auth(member)) is True
        assert child.can_edit(Auth(member)) is False

        grandchild = ProjectFactory(parent=child)
        assert grandchild.can_view(Auth(member)) is True
        assert grandchild.can_edit(Auth(member)) is False

    def test_node_has_permission(self, project, manager, member, osf_group):
        assert project.can_view(Auth(member)) is False
        project.add_osf_group(osf_group, READ)
        assert project.has_permission(member, READ) is True
        assert project.has_permission(member, WRITE) is False
        assert osf_group.get_permission_to_node(project) == READ

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, WRITE)
        assert project.has_permission(member, READ) is True
        assert project.has_permission(member, WRITE) is True
        assert project.has_permission(member, ADMIN) is False
        assert osf_group.get_permission_to_node(project) == WRITE

        child = ProjectFactory(parent=project)
        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, ADMIN)
        assert osf_group.get_permission_to_node(project) == ADMIN
        # implicit OSF Group admin
        assert child.has_permission(member, ADMIN) is False
        assert child.has_permission(member, READ) is True
        assert osf_group.get_permission_to_node(child) is None

        grandchild = ProjectFactory(parent=child)
        assert grandchild.has_permission(member, WRITE) is False
        assert grandchild.has_permission(member, READ) is True

    def test_node_get_permissions_override(self, project, manager, member, osf_group):
        project.add_osf_group(osf_group, WRITE)
        assert set(project.get_permissions(member)) == set([READ, WRITE])

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, READ)
        assert set(project.get_permissions(member)) == set([READ])

        anon = AnonymousUser()
        assert project.get_permissions(anon) == []

    def test_is_contributor(self, project, manager, member, osf_group):
        assert project.is_contributor(manager) is True
        assert project.is_contributor(member) is False
        project.add_osf_group(osf_group, READ, auth=Auth(project.creator))
        assert project.is_contributor(member) is False
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.is_contributor_or_group_member(member) is False
        project.add_contributor(member, READ)
        assert project.is_contributor(member) is True
        assert project.is_contributor_or_group_member(member) is True

    def test_is_contributor_or_group_member(self, project, manager, member, osf_group):
        project.add_osf_group(osf_group, ADMIN, auth=Auth(project.creator))
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.is_contributor_or_group_member(member) is False
        project.add_osf_group(osf_group, WRITE, auth=Auth(project.creator))
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.is_contributor_or_group_member(member) is False
        project.add_osf_group(osf_group, READ, auth=Auth(project.creator))
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        osf_group.add_unregistered_member('jane', 'janedoe@cos.io', Auth(manager))
        unreg = osf_group.members.get(username='janedoe@cos.io')
        assert unreg.is_registered is False
        assert project.is_contributor_or_group_member(unreg) is False
        project.add_osf_group(osf_group, READ, auth=Auth(project.creator))
        assert project.is_contributor_or_group_member(unreg) is True

        child = ProjectFactory(parent=project)
        assert child.is_contributor_or_group_member(manager) is False

    def test_node_object_can_view_osfgroups(self, manager, member, project, osf_group):
        project.add_contributor(member, ADMIN, save=True)  # Member is explicit admin contributor on project
        child = NodeFactory(parent=project, creator=manager)  # Member is implicit admin on child
        grandchild = NodeFactory(parent=child, creator=manager)  # Member is implicit admin on grandchild

        project_two = ProjectFactory(creator=manager)
        project_two.add_osf_group(osf_group, ADMIN)  # Member has admin permissions to project_two through osf_group
        child_two = NodeFactory(parent=project_two, creator=manager)  # Member has implicit admin on child_two through osf_group
        grandchild_two = NodeFactory(parent=child_two, creator=manager)  # Member has implicit admin perms on grandchild_two through osf_group
        can_view = Node.objects.can_view(member)
        assert len(can_view) == 6
        assert set(list(can_view.values_list('id', flat=True))) == set((project.id,
                                                                        child.id,
                                                                        grandchild.id,
                                                                        project_two.id,
                                                                        child_two.id,
                                                                        grandchild_two.id))

        grandchild_two.is_deleted = True
        grandchild_two.save()
        can_view = Node.objects.can_view(member)
        assert len(can_view) == 5
        assert grandchild_two not in can_view

    def test_parent_admin_users_osf_groups(self, manager, member, user_two, project, osf_group):
        child = NodeFactory(parent=project, creator=manager)
        project.add_osf_group(osf_group, ADMIN)
        # Manager has explict admin to child, member has implicit admin.
        # Manager should be in admin_users, member should be in parent_admin_users
        admin_users = child.get_users_with_perm(ADMIN)
        assert manager in admin_users
        assert member not in admin_users

        assert manager not in child.parent_admin_users
        assert member in child.parent_admin_users

        user_two.is_superuser = True
        user_two.save()

        assert user_two not in admin_users
        assert user_two not in child.parent_admin_users


class TestOSFGroupLogging:
    def test_logging(self, project, manager, member):
        # Calling actions 2x in this test to assert we're not getting double logs
        group = OSFGroup.objects.create(name='My Lab', creator_id=manager.id)
        assert group.logs.count() == 2
        log = group.logs.last()
        assert log.action == OSFGroupLog.GROUP_CREATED
        assert log.user == manager
        assert log.user == manager
        assert log.params['group'] == group._id

        log = group.logs.first()
        assert log.action == OSFGroupLog.MANAGER_ADDED
        assert log.params['group'] == group._id

        group.make_member(member, Auth(manager))
        group.make_member(member, Auth(manager))
        assert group.logs.count() == 3
        log = group.logs.first()
        assert log.action == OSFGroupLog.MEMBER_ADDED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['user'] == member._id

        group.make_manager(member, Auth(manager))
        group.make_manager(member, Auth(manager))
        assert group.logs.count() == 4
        log = group.logs.first()
        assert log.action == OSFGroupLog.ROLE_UPDATED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['user'] == member._id
        assert log.params['new_role'] == MANAGER

        group.make_member(member, Auth(manager))
        group.make_member(member, Auth(manager))
        log = group.logs.first()
        assert group.logs.count() == 5
        assert log.action == OSFGroupLog.ROLE_UPDATED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['user'] == member._id
        assert log.params['new_role'] == MEMBER

        group.remove_member(member, Auth(manager))
        group.remove_member(member, Auth(manager))
        assert group.logs.count() == 6
        log = group.logs.first()
        assert log.action == OSFGroupLog.MEMBER_REMOVED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['user'] == member._id

        group.set_group_name('New Name', Auth(manager))
        group.set_group_name('New Name', Auth(manager))
        assert group.logs.count() == 7
        log = group.logs.first()
        assert log.action == OSFGroupLog.EDITED_NAME
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['name_original'] == 'My Lab'

        project.add_osf_group(group, WRITE, Auth(manager))
        project.add_osf_group(group, WRITE, Auth(manager))
        assert group.logs.count() == 8
        log = group.logs.first()
        assert log.action == OSFGroupLog.NODE_CONNECTED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['node'] == project._id
        assert log.params['permission'] == WRITE
        node_log = project.logs.first()

        assert node_log.action == NodeLog.GROUP_ADDED
        assert node_log.user == manager
        assert node_log.params['group'] == group._id
        assert node_log.params['node'] == project._id
        assert node_log.params['permission'] == WRITE

        project.update_osf_group(group, READ, Auth(manager))
        project.update_osf_group(group, READ, Auth(manager))
        log = group.logs.first()
        assert group.logs.count() == 9
        assert log.action == OSFGroupLog.NODE_PERMS_UPDATED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['node'] == project._id
        assert log.params['permission'] == READ
        node_log = project.logs.first()

        assert node_log.action == NodeLog.GROUP_UPDATED
        assert node_log.user == manager
        assert node_log.params['group'] == group._id
        assert node_log.params['node'] == project._id
        assert node_log.params['permission'] == READ

        project.remove_osf_group(group, Auth(manager))
        project.remove_osf_group(group, Auth(manager))
        assert group.logs.count() == 10
        log = group.logs.first()
        assert log.action == OSFGroupLog.NODE_DISCONNECTED
        assert log.user == manager
        assert log.params['group'] == group._id
        assert log.params['node'] == project._id
        node_log = project.logs.first()

        assert node_log.action == NodeLog.GROUP_REMOVED
        assert node_log.user == manager
        assert node_log.params['group'] == group._id
        assert node_log.params['node'] == project._id

        project.add_osf_group(group, WRITE, Auth(manager))
        project.add_osf_group(group, WRITE, Auth(manager))
        group.remove_group(auth=Auth(manager))

        node_log = project.logs.first()
        assert node_log.action == NodeLog.GROUP_REMOVED
        assert node_log.user == manager
        assert node_log.params['group'] == group._id
        assert node_log.params['node'] == project._id


class TestRemovingContributorOrGroupMembers:
    """
    Post OSF-Groups, the same kinds of checks you run when removing a contributor,
    need to be run when a group is removed from a node (or a user is removed from a group,
    or the group is deleted altogether).

    The actions are only executed if the user has no perms at all: no contributorship,
    and no group membership
    """

    @pytest.fixture()
    def project(self, user_two, user_three, external_account):
        project = ProjectFactory(creator=user_two)
        project.add_contributor(user_three, ADMIN)
        project.add_addon('github', auth=Auth(user_two))
        project.creator.add_addon('github')
        project.creator.external_accounts.add(external_account)
        project.creator.save()
        return project

    @pytest.fixture()
    def file(self, project, user_two):
        filename = 'my_file.txt'
        project_file = OsfStorageFile.create(
            target_object_id=project.id,
            target_content_type=ContentType.objects.get_for_model(project),
            path='/{}'.format(filename),
            name=filename,
            materialized_path='/{}'.format(filename))

        project_file.save()
        from addons.osfstorage import settings as osfstorage_settings

        project_file.create_version(user_two, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save
        project_file.checkout = user_two
        project_file.save()
        return project_file

    @pytest.fixture()
    def external_account(self):
        return factories.GitHubAccountFactory()

    @pytest.fixture()
    def node_settings(self, project, external_account):
        node_settings = project.get_addon('github')
        user_settings = project.creator.get_addon('github')
        user_settings.oauth_grants[project._id] = {external_account._id: []}
        user_settings.save()
        node_settings.user_settings = user_settings
        node_settings.user = 'Queen'
        node_settings.repo = 'Sheer-Heart-Attack'
        node_settings.external_account = external_account
        node_settings.save()
        node_settings.set_auth
        return node_settings

    def test_remove_contributor_no_member_perms(self, project, node_settings, user_two, user_three, request_context, file):
        assert project.get_addon('github').user_settings is not None
        assert file.checkout is not None
        assert len(get_all_node_subscriptions(user_two, project)) == 2
        project.remove_contributor(user_two, Auth(user_three))
        project.reload()

        assert project.get_addon('github').user_settings is None
        file.reload()
        assert file.checkout is None
        assert len(get_all_node_subscriptions(user_two, project)) == 0

    def test_remove_group_from_node_no_contributor_perms(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)
        # Manually removing contributor
        contrib_obj = project.contributor_set.get(user=user_two)
        contrib_obj.delete()
        project.clear_permissions(user_two)

        assert project.is_contributor(user_two) is False
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        project.remove_osf_group(group)
        project.reload()

        assert project.get_addon('github').user_settings is None
        file.reload()
        assert file.checkout is None
        assert len(get_all_node_subscriptions(user_two, project)) == 0

    def test_remove_member_no_contributor_perms(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)
        group.make_manager(user_three)
        # Manually removing contributor
        contrib_obj = project.contributor_set.get(user=user_two)
        contrib_obj.delete()
        project.clear_permissions(user_two)

        assert project.is_contributor(user_two) is False
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        group.remove_member(user_two)
        project.reload()

        assert project.get_addon('github').user_settings is None
        file.reload()
        assert file.checkout is None
        assert len(get_all_node_subscriptions(user_two, project)) == 0

    def test_delete_group_no_contributor_perms(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)
        group.make_manager(user_three)
        # Manually removing contributor
        contrib_obj = project.contributor_set.get(user=user_two)
        contrib_obj.delete()
        project.clear_permissions(user_two)

        assert project.is_contributor(user_two) is False
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        group.remove_group()
        project.reload()

        assert project.get_addon('github').user_settings is None
        file.reload()
        assert file.checkout is None
        assert len(get_all_node_subscriptions(user_two, project)) == 0

    def test_remove_contributor_also_member(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)

        assert project.is_contributor(user_two) is True
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        project.remove_osf_group(group)
        project.reload()

        assert project.get_addon('github').user_settings is not None
        file.reload()
        assert file.checkout is not None
        assert len(get_all_node_subscriptions(user_two, project)) == 2

    def test_remove_osf_group_from_node_also_member(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)

        assert project.is_contributor(user_two) is True
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        project.remove_osf_group(group)
        project.reload()

        assert project.get_addon('github').user_settings is not None
        file.reload()
        assert file.checkout is not None
        assert len(get_all_node_subscriptions(user_two, project)) == 2

    def test_remove_member_also_contributor(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        group.make_manager(user_three)
        project.add_osf_group(group, ADMIN)

        assert project.is_contributor(user_two) is True
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        group.remove_member(user_two)
        project.reload()
        assert project.get_addon('github').user_settings is not None
        file.reload()
        assert file.checkout is not None
        assert len(get_all_node_subscriptions(user_two, project)) == 2

    def test_delete_group_also_contributor(self, project, node_settings, user_two, user_three, request_context, file):
        group = OSFGroupFactory(creator=user_two)
        project.add_osf_group(group, ADMIN)
        group.make_manager(user_three)

        assert project.is_contributor(user_two) is True
        assert project.is_contributor_or_group_member(user_two) is True
        assert node_settings.user_settings is not None
        group.remove_group()
        project.reload()
        assert project.get_addon('github').user_settings is not None
        file.reload()
        assert file.checkout is not None
        assert len(get_all_node_subscriptions(user_two, project)) == 2
