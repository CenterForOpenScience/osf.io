import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group

from framework.auth import Auth
from django.contrib.auth.models import AnonymousUser
from framework.exceptions import PermissionsError
from osf.models import OSFGroup, Node, OSFUser
from .factories import (
    NodeFactory,
    ProjectFactory,
    UserFactory,
    OSFGroupFactory
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def manager():
    return UserFactory()

@pytest.fixture()
def member():
    return UserFactory()

@pytest.fixture()
def user_two():
    return UserFactory()

@pytest.fixture()
def user_three():
    return UserFactory()

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
        assert osf_group.has_permission(manager, 'manage') is True
        assert osf_group.has_permission(user_two, 'manage') is False

        assert manager in osf_group.managers
        assert manager in osf_group.members

    def test_make_manager(self, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_manager(user_two, Auth(member))

        # manage permissions
        osf_group.make_manager(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, 'manage') is True
        assert user_two in osf_group.managers
        assert user_two in osf_group.members

        # upgrade to manager
        osf_group.make_manager(member, Auth(manager))
        assert osf_group.has_permission(member, 'manage') is True
        assert member in osf_group.managers
        assert member in osf_group.members

    def test_make_member(self, manager, member, user_two, user_three, osf_group):
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.make_member(user_two, Auth(member))

        # manage permissions
        osf_group.make_member(user_two, Auth(manager))
        assert osf_group.has_permission(user_two, 'manage') is False
        assert user_two not in osf_group.managers
        assert user_two in osf_group.members

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

    def test_add_unregistered_member(self, manager, member, osf_group, user_two):
        test_fullname = 'Test User'
        test_email = 'test_member@cos.io'
        test_manager_email = 'test_manager@cos.io'

        # Email already exists
        with pytest.raises(ValidationError):
            osf_group.add_unregistered_member(test_fullname, user_two.username, auth=Auth(manager))

        # Test need manager perms to add
        with pytest.raises(PermissionsError):
            osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(member))

        # Add member
        osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(manager))
        unreg_user = OSFUser.objects.get(username=test_email)
        assert unreg_user in osf_group.members
        assert unreg_user not in osf_group.managers
        # Unreg user hasn't claimed account, so they have no permissions, even though they belong to member group
        assert osf_group.has_permission(unreg_user, 'member') is False
        assert osf_group._id in unreg_user.unclaimed_records

        # Attempt to add unreg user as a member
        with pytest.raises(ValidationError):
            osf_group.add_unregistered_member(test_fullname, test_email, auth=Auth(manager))

        # Add unregistered manager
        osf_group.add_unregistered_member(test_fullname, test_manager_email, auth=Auth(manager), role='manager')
        unreg_manager = OSFUser.objects.get(username=test_manager_email)
        assert unreg_manager in osf_group.members
        assert unreg_manager in osf_group.managers
        # Unreg manager hasn't claimed account, so they have no permissions, even though they belong to member group
        assert osf_group.has_permission(unreg_manager, 'member') is False
        assert osf_group._id in unreg_manager.unclaimed_records

    def test_remove_member(self, manager, member, user_three, osf_group):
        new_member = UserFactory()
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

        # Attempt to remove manager using this method
        osf_group.make_manager(user_three)
        with pytest.raises(ValueError):
            osf_group.remove_member(user_three)

        # Remove self - member can remove themselves
        osf_group.remove_member(member, Auth(member))
        assert member not in osf_group.managers
        assert member not in osf_group.members

    def test_remove_manager(self, manager, member, user_three, osf_group):
        new_manager = UserFactory()
        osf_group.make_manager(new_manager)
        # no permissions
        with pytest.raises(PermissionsError):
            osf_group.remove_manager(new_manager, Auth(user_three))

        # member only
        with pytest.raises(PermissionsError):
            osf_group.remove_manager(new_manager, Auth(member))

        # manage permissions
        osf_group.remove_manager(new_manager, Auth(manager))
        assert new_manager not in osf_group.managers
        assert new_manager not in osf_group.members

        # can't remove last manager
        with pytest.raises(ValueError):
            osf_group.remove_manager(manager, Auth(manager))
        assert manager in osf_group.managers
        assert manager in osf_group.members

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

    def test_user_groups_property(self, manager, member, osf_group):
        assert osf_group in manager.osf_groups
        assert osf_group in member.osf_groups

        other_group = OSFGroupFactory()

        assert other_group not in manager.osf_groups
        assert other_group not in member.osf_groups

    def test_osf_group_nodes(self, manager, member, project, osf_group):
        nodes = osf_group.nodes
        assert len(nodes) == 0
        project.add_osf_group(osf_group, 'read')
        assert project in osf_group.nodes

        project_two = ProjectFactory(creator=manager)
        project_two.add_osf_group(osf_group, 'write')
        assert len(osf_group.nodes) == 2
        assert project_two in osf_group.nodes

    def test_add_osf_group_to_node(self, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, 'write', auth=Auth(member))

        # Non-admin on project
        project.add_contributor(user_two, 'write')
        project.save()
        with pytest.raises(PermissionsError):
            project.add_osf_group(osf_group, 'write', auth=Auth(user_two))

        project.add_osf_group(osf_group, 'read', auth=Auth(manager))
        # Manager was already a node admin
        assert project.has_permission(manager, 'admin') is True
        assert project.has_permission(manager, 'write') is True
        assert project.has_permission(manager, 'read') is True

        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is True

        project.add_osf_group(osf_group, 'write', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

    def test_add_osf_group_to_node_default_permission(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, auth=Auth(manager))

        assert project.has_permission(manager, 'admin') is True
        assert project.has_permission(manager, 'write') is True
        assert project.has_permission(manager, 'read') is True

        # osf_group given write permissions by default
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

    def test_update_osf_group_node(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, 'admin')

        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.update_osf_group(osf_group, 'read')
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is True

        project.update_osf_group(osf_group, 'write')
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.update_osf_group(osf_group, 'admin')
        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

    def test_remove_osf_group_from_node(self, manager, member, user_two, osf_group, project):
        # noncontributor
        with pytest.raises(PermissionsError):
            project.remove_osf_group(osf_group, auth=Auth(member))

        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert project.has_permission(member, 'admin') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'read') is True

        project.remove_osf_group(osf_group, auth=Auth(manager))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is False

        # Project admin who does not belong to the manager group can remove the group
        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        project.add_contributor(user_two, 'admin')
        project.save()
        project.remove_osf_group(osf_group, auth=Auth(user_two))
        assert project.has_permission(member, 'admin') is False
        assert project.has_permission(member, 'write') is False
        assert project.has_permission(member, 'read') is False

    def test_node_groups_property(self, manager, member, osf_group, project):
        project.add_osf_group(osf_group, 'admin', auth=Auth(manager))
        assert osf_group.member_group in project.osf_groups
        assert len(project.osf_groups) == 1

        group_two = OSFGroupFactory(creator=manager)
        project.add_osf_group(group_two, 'admin', auth=Auth(manager))
        assert group_two.member_group in project.osf_groups
        assert len(project.osf_groups) == 2

    def test_belongs_to_osfgroup_property(self, manager, member, user_two, osf_group):
        assert osf_group.belongs_to_osfgroup(manager) is True
        assert osf_group.belongs_to_osfgroup(member) is True
        assert osf_group.belongs_to_osfgroup(user_two) is False

    def test_node_object_can_view_osfgroups(self, manager, member, project, osf_group):
        project.add_contributor(member, 'admin', save=True)  # Member is explicit admin contributor on project
        child = NodeFactory(parent=project, creator=manager)  # Member is implicit admin on child
        grandchild = NodeFactory(parent=child, creator=manager)  # Member is implicit admin on grandchild

        project_two = ProjectFactory(creator=manager)
        project_two.add_osf_group(osf_group, 'admin')  # Member has admin permissions to project_two through osf_group
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

    def test_parent_admin_users_osf_groups(self, manager, member, project, osf_group):
        child = NodeFactory(parent=project, creator=manager)
        project.add_osf_group(osf_group, 'admin')
        # Manager has explict admin to child, member has implicit admin.
        # Manager should be in admin_contributors, member should be in parent_admin_contributors

        assert manager in child.admin_users
        assert member not in child.admin_users

        assert manager not in child.parent_admin_users
        assert member in child.parent_admin_users

    def test_get_users_with_perm_osf_groups(self, project, manager, member, osf_group):
        # Explicitly added as a contributor
        read_users = project.get_users_with_perm('read')
        write_users = project.get_users_with_perm('write')
        admin_users = project.get_users_with_perm('admin')
        assert len(project.get_users_with_perm('read')) == 1
        assert len(project.get_users_with_perm('write')) == 1
        assert len(project.get_users_with_perm('admin')) == 1
        assert manager in read_users
        assert manager in write_users
        assert manager in admin_users

        # Added through osf groups
        project.add_osf_group(osf_group, 'write')
        read_users = project.get_users_with_perm('read')
        write_users = project.get_users_with_perm('write')
        admin_users = project.get_users_with_perm('admin')
        assert len(project.get_users_with_perm('read')) == 2
        assert len(project.get_users_with_perm('write')) == 2
        assert len(project.get_users_with_perm('admin')) == 1
        assert member in read_users
        assert member in write_users
        assert member not in admin_users

    def test_osf_group_node_can_view(self, project, manager, member, osf_group):
        assert project.can_view(Auth(member)) is False
        project.add_osf_group(osf_group, 'read')
        assert project.can_view(Auth(member)) is True
        assert project.can_edit(Auth(member)) is False

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, 'write')
        assert project.can_view(Auth(member)) is True
        assert project.can_edit(Auth(member)) is True

        child = ProjectFactory(parent=project)
        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, 'admin')
        # implicit OSF Group admin
        assert child.can_view(Auth(member)) is True
        assert child.can_edit(Auth(member)) is False

        grandchild = ProjectFactory(parent=child)
        assert grandchild.can_view(Auth(member)) is True
        assert grandchild.can_edit(Auth(member)) is False

    def test_node_has_permission(self, project, manager, member, osf_group):
        assert project.can_view(Auth(member)) is False
        project.add_osf_group(osf_group, 'read')
        assert project.has_permission(member, 'read') is True
        assert project.has_permission(member, 'write') is False

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, 'write')
        assert project.has_permission(member, 'read') is True
        assert project.has_permission(member, 'write') is True
        assert project.has_permission(member, 'admin') is False

        child = ProjectFactory(parent=project)
        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, 'admin')
        # implicit OSF Group admin
        assert child.has_permission(member, 'admin') is False
        assert child.has_permission(member, 'read') is True

        grandchild = ProjectFactory(parent=child)
        assert grandchild.has_permission(member, 'write') is False
        assert grandchild.has_permission(member, 'read') is True

    def test_node_get_permissions_override(self, project, manager, member, osf_group):
        project.add_osf_group(osf_group, 'write')
        assert set(project.get_permissions(member)) == set(['write_node', 'read_node'])

        project.remove_osf_group(osf_group)
        project.add_osf_group(osf_group, 'read')
        assert set(project.get_permissions(member)) == set(['read_node'])

        anon = AnonymousUser()
        assert project.get_permissions(anon) == []

    def test_is_contributor(self, project, manager, member, osf_group):
        assert project.is_contributor(manager) is True
        assert project.is_contributor(member) is False
        project.add_osf_group(osf_group, 'read')
        assert project.is_contributor(member) is False
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group)
        assert project.is_contributor_or_group_member(member) is False
        project.add_contributor(member, 'read')
        assert project.is_contributor(member) is True
        assert project.is_contributor_or_group_member(member) is True

    def test_is_contributor_or_group_member(self, project, manager, member, osf_group):
        project.add_osf_group(osf_group, 'admin')
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group)
        assert project.is_contributor_or_group_member(member) is False
        project.add_osf_group(osf_group, 'write')
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group)
        assert project.is_contributor_or_group_member(member) is False
        project.add_osf_group(osf_group, 'read')
        assert project.is_contributor_or_group_member(member) is True

        project.remove_osf_group(osf_group)
