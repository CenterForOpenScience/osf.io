import datetime

from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.models import PreprintService
import mock
import pytest
import pytz
import requests

class TestPreprintContributors:
    def test_creator_is_added_as_contributor(self, fake):
        user = UserFactory()
        node = Node(
            title=fake.bs(),
            creator=user
        )
        node.save()
        assert node.is_contributor(user) is True
        contributor = Contributor.objects.get(user=user, node=node)
        assert contributor.visible is True
        assert contributor.read is True
        assert contributor.write is True
        assert contributor.admin is True


# Copied from tests/test_models.py
class TestContributorMethods:
    def test_add_contributor(self, node, user, auth):
        # A user is added as a contributor
        user2 = UserFactory()
        node.add_contributor(contributor=user2, auth=auth)
        node.save()
        assert node.is_contributor(user2) is True
        last_log = node.logs.all().order_by('-date')[0]
        assert last_log.action == 'contributor_added'
        assert last_log.params['contributors'] == [user2._id]

        assert user2 in user.recently_added.all()

    def test_add_contributors(self, node, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        node.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write', 'admin'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': False}
            ],
            auth=auth
        )
        last_log = node.logs.all().order_by('-date')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )
        assert node.is_contributor(user1)
        assert node.is_contributor(user2)
        assert user1._id in node.visible_contributor_ids
        assert user2._id not in node.visible_contributor_ids
        assert node.get_permissions(user1) == [permissions.READ, permissions.WRITE, permissions.ADMIN]
        assert node.get_permissions(user2) == [permissions.READ, permissions.WRITE]
        last_log = node.logs.all().order_by('-date')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )

    def test_cant_add_creator_as_contributor_twice(self, node, user):
        node.add_contributor(contributor=user)
        node.save()
        assert len(node.contributors) == 1

    def test_cant_add_same_contributor_twice(self, node):
        contrib = UserFactory()
        node.add_contributor(contributor=contrib)
        node.save()
        node.add_contributor(contributor=contrib)
        node.save()
        assert len(node.contributors) == 2

    def test_remove_unregistered_conributor_removes_unclaimed_record(self, node, auth):
        new_user = node.add_unregistered_contributor(fullname='David Davidson',
            email='david@davidson.com', auth=auth)
        node.save()
        assert node.is_contributor(new_user)  # sanity check
        assert node._primary_key in new_user.unclaimed_records
        node.remove_contributor(
            auth=auth,
            contributor=new_user
        )
        node.save()
        new_user.refresh_from_db()
        assert node._primary_key not in new_user.unclaimed_records

    def test_is_contributor(self, node):
        contrib, noncontrib = UserFactory(), UserFactory()
        Contributor.objects.create(user=contrib, node=node)

        assert node.is_contributor(contrib) is True
        assert node.is_contributor(noncontrib) is False
        assert node.is_contributor(None) is False

    def test_visible_contributor_ids(self, node, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        Contributor.objects.create(user=visible_contrib, node=node, visible=True)
        Contributor.objects.create(user=invisible_contrib, node=node, visible=False)
        assert visible_contrib._id in node.visible_contributor_ids
        assert invisible_contrib._id not in node.visible_contributor_ids

    def test_visible_contributors(self, node, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        Contributor.objects.create(user=visible_contrib, node=node, visible=True)
        Contributor.objects.create(user=invisible_contrib, node=node, visible=False)
        assert visible_contrib in node.visible_contributors
        assert invisible_contrib not in node.visible_contributors

    def test_set_visible_false(self, node, auth):
        contrib = UserFactory()
        Contributor.objects.create(user=contrib, node=node, visible=True)
        node.set_visible(contrib, visible=False, auth=auth)
        node.save()
        assert Contributor.objects.filter(user=contrib, node=node, visible=False).exists() is True

        last_log = node.logs.all().order_by('-date')[0]
        assert last_log.user == auth.user
        assert last_log.action == NodeLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_set_visible_true(self, node, auth):
        contrib = UserFactory()
        Contributor.objects.create(user=contrib, node=node, visible=False)
        node.set_visible(contrib, visible=True, auth=auth)
        node.save()
        assert Contributor.objects.filter(user=contrib, node=node, visible=True).exists() is True

        last_log = node.logs.all().order_by('-date')[0]
        assert last_log.user == auth.user
        assert last_log.action == NodeLog.MADE_CONTRIBUTOR_VISIBLE

    def test_set_visible_is_noop_if_visibility_is_unchanged(self, node, auth):
        visible, invisible = UserFactory(), UserFactory()
        Contributor.objects.create(user=visible, node=node, visible=True)
        Contributor.objects.create(user=invisible, node=node, visible=False)
        original_log_count = node.logs.count()
        node.set_visible(invisible, visible=False, auth=auth)
        node.set_visible(visible, visible=True, auth=auth)
        node.save()
        assert node.logs.count() == original_log_count

    def test_set_visible_contributor_with_only_one_contributor(self, node, user):
        with pytest.raises(ValueError) as excinfo:
            node.set_visible(user=user, visible=False, auth=None)
        assert excinfo.value.message == 'Must have at least one visible contributor'

    def test_set_visible_missing(self, node):
        with pytest.raises(ValueError):
            node.set_visible(UserFactory(), True)

    def test_copy_contributors_from_adds_contributors(self, node):
        contrib, contrib2 = UserFactory(), UserFactory()
        Contributor.objects.create(user=contrib, node=node, visible=True)
        Contributor.objects.create(user=contrib2, node=node, visible=False)

        node2 = NodeFactory()
        node2.copy_contributors_from(node)

        assert node2.is_contributor(contrib)
        assert node2.is_contributor(contrib2)

        assert node.is_contributor(contrib)
        assert node.is_contributor(contrib2)

    def test_copy_contributors_from_preserves_visibility(self, node):
        visible, invisible = UserFactory(), UserFactory()
        Contributor.objects.create(user=visible, node=node, visible=True)
        Contributor.objects.create(user=invisible, node=node, visible=False)

        node2 = NodeFactory()
        node2.copy_contributors_from(node)

        assert Contributor.objects.get(node=node, user=visible).visible is True
        assert Contributor.objects.get(node=node, user=invisible).visible is False

    def test_copy_contributors_from_preserves_permissions(self, node):
        read, admin = UserFactory(), UserFactory()
        Contributor.objects.create(user=read, node=node, read=True, write=False, admin=False)
        Contributor.objects.create(user=admin, node=node, read=True, write=True, admin=True)

        node2 = NodeFactory()
        node2.copy_contributors_from(node)

        assert node2.has_permission(read, 'read') is True
        assert node2.has_permission(read, 'write') is False
        assert node2.has_permission(admin, 'admin') is True

    def test_remove_contributor(self, node, auth):
        # A user is added as a contributor
        user2 = UserFactory()
        node.add_contributor(contributor=user2, auth=auth, save=True)
        assert user2 in node.contributors
        # The user is removed
        with disconnected_from_listeners(contributor_removed):
            node.remove_contributor(auth=auth, contributor=user2)
        node.reload()

        assert user2 not in node.contributors
        assert node.get_permissions(user2) == []
        assert node.logs.latest().action == 'contributor_removed'
        assert node.logs.latest().params['contributors'] == [user2._id]

    def test_remove_contributors(self, node, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        node.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': True}
            ],
            auth=auth
        )
        assert user1 in node.contributors
        assert user2 in node.contributors

        with disconnected_from_listeners(contributor_removed):
            node.remove_contributors(auth=auth, contributors=[user1, user2], save=True)
        node.reload()

        assert user1 not in node.contributors
        assert user2 not in node.contributors
        assert node.get_permissions(user1) == []
        assert node.get_permissions(user2) == []
        assert node.logs.latest().action == 'contributor_removed'

    def test_replace_contributor(self, node):
        contrib = UserFactory()
        node.add_contributor(contrib, auth=Auth(node.creator))
        node.save()
        assert contrib in node.contributors.all()  # sanity check
        replacer = UserFactory()
        old_length = node.contributors.count()
        node.replace_contributor(contrib, replacer)
        node.save()
        new_length = node.contributors.count()
        assert contrib not in node.contributors.all()
        assert replacer in node.contributors.all()
        assert old_length == new_length

        # test unclaimed_records is removed
        assert (
            node._id not in
            contrib.unclaimed_records.keys()
        )

    def test_permission_override_on_readded_contributor(self, node, user):

        # A child node created
        child_node = NodeFactory(parent=node, creator=user)

        # A user is added as with read permission
        user2 = UserFactory()
        child_node.add_contributor(user2, permissions=['read'])

        # user is readded with permission admin
        child_node.add_contributor(user2, permissions=['read', 'write', 'admin'])
        child_node.save()

        assert child_node.has_permission(user2, 'admin') is True

    def test_permission_override_fails_if_no_admins(self, node, user):
        # User has admin permissions because they are the creator
        # Cannot lower permissions
        with pytest.raises(NodeStateError):
            node.add_contributor(user, permissions=['read', 'write'])

    def test_update_contributor(self, node, auth):
        new_contrib = AuthUserFactory()
        node.add_contributor(new_contrib, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS, auth=auth)

        assert node.get_permissions(new_contrib) == DEFAULT_CONTRIBUTOR_PERMISSIONS
        assert node.get_visible(new_contrib) is True

        node.update_contributor(
            new_contrib,
            READ,
            False,
            auth=auth
        )
        assert node.get_permissions(new_contrib) == [READ]
        assert node.get_visible(new_contrib) is False

    def test_update_contributor_non_admin_raises_error(self, node, auth):
        non_admin = AuthUserFactory()
        node.add_contributor(
            non_admin,
            permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS,
            auth=auth
        )
        with pytest.raises(PermissionsError):
            node.update_contributor(
                non_admin,
                None,
                False,
                auth=Auth(non_admin)
            )

    def test_update_contributor_only_admin_raises_error(self, node, auth):
        with pytest.raises(NodeStateError):
            node.update_contributor(
                auth.user,
                WRITE,
                True,
                auth=auth
            )

    def test_update_contributor_non_contrib_raises_error(self, node, auth):
        non_contrib = AuthUserFactory()
        with pytest.raises(ValueError):
            node.update_contributor(
                non_contrib,
                ADMIN,
                True,
                auth=auth
            )


# Copied from tests/test_models.py
class TestNodeAddContributorRegisteredOrNot:

    def test_add_contributor_user_id(self, user, node):
        registered_user = UserFactory()
        contributor_obj = node.add_contributor_registered_or_not(auth=Auth(user), user_id=registered_user._id, save=True)
        contributor = contributor_obj.user
        assert contributor in node.contributors
        assert contributor.is_registered is True

    def test_add_contributor_user_id_already_contributor(self, user, node):
        with pytest.raises(ValidationError) as excinfo:
            node.add_contributor_registered_or_not(auth=Auth(user), user_id=user._id, save=True)
        assert 'is already a contributor' in excinfo.value.message

    def test_add_contributor_invalid_user_id(self, user, node):
        with pytest.raises(ValueError) as excinfo:
            node.add_contributor_registered_or_not(auth=Auth(user), user_id='abcde', save=True)
        assert 'was not found' in excinfo.value.message

    def test_add_contributor_fullname_email(self, user, node):
        contributor_obj = node.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe', email='jane@doe.com')
        contributor = contributor_obj.user
        assert contributor in node.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname(self, user, node):
        contributor_obj = node.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe')
        contributor = contributor_obj.user
        assert contributor in node.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname_email_already_exists(self, user, node):
        registered_user = UserFactory()
        contributor_obj = node.add_contributor_registered_or_not(auth=Auth(user), full_name='F Mercury', email=registered_user.username)
        contributor = contributor_obj.user
        assert contributor in node.contributors
        assert contributor.is_registered is True

class TestContributorProperties:

    def test_admin_contributors(self, user):
        project = ProjectFactory(creator=user)
        assert list(project.admin_contributors) == [user]
        child1 = ProjectFactory(parent=project)
        child2 = ProjectFactory(parent=child1)
        assert list(child1.admin_contributors) == sorted([project.creator, child1.creator], key=lambda user: user.family_name)
        assert (
            list(child2.admin_contributors) ==
            sorted([project.creator, child1.creator, child2.creator], key=lambda user: user.family_name)
        )
        admin = UserFactory()
        project.add_contributor(admin, auth=Auth(project.creator), permissions=['read', 'write', 'admin'])
        project.set_permissions(project.creator, ['read', 'write'])
        project.save()
        assert list(child1.admin_contributors) == sorted([child1.creator, admin], key=lambda user: user.family_name)
        assert list(child2.admin_contributors) == sorted([child2.creator, child1.creator, admin], key=lambda user: user.family_name)

    def test_admin_contributor_ids(self, user):
        project = ProjectFactory(creator=user)
        assert project.admin_contributor_ids == {user._id}
        child1 = ProjectFactory(parent=project)
        child2 = ProjectFactory(parent=child1)
        assert child1.admin_contributor_ids == {project.creator._id, child1.creator._id}
        assert child2.admin_contributor_ids == {project.creator._id, child1.creator._id, child2.creator._id}
        admin = UserFactory()
        project.add_contributor(admin, auth=Auth(project.creator), permissions=['read', 'write', 'admin'])
        project.set_permissions(project.creator, ['read', 'write'])
        project.save()
        assert child1.admin_contributor_ids == {child1.creator._id, admin._id}
        assert child2.admin_contributor_ids == {child2.creator._id, child1.creator._id, admin._id}


class TestContributorAddedSignal:

    # Override disconnected signals from conftest
    @pytest.fixture(autouse=True)
    def disconnected_signals(self):
        return None

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_add_contributors_sends_contributor_added_signal(self, mock_send_mail, node, auth):
        user = UserFactory()
        contributors = [{
            'user': user,
            'visible': True,
            'permissions': ['read', 'write']
        }]
        with capture_signals() as mock_signals:
            node.add_contributors(contributors=contributors, auth=auth)
            node.save()
            assert node.is_contributor(user)
            assert mock_signals.signals_sent() == set([contributor_added])


class TestContributorVisibility:

    @pytest.fixture()
    def user2(self):
        return UserFactory()

    @pytest.fixture()
    def project(self, user, user2):
        p = ProjectFactory(creator=user)
        p.add_contributor(user2)
        #p.save()
        return p

    def test_get_visible_true(self, project):
        assert project.get_visible(project.creator) is True

    def test_get_visible_false(self, project):
        project.set_visible(project.creator, False)
        assert project.get_visible(project.creator) is False

    def test_make_invisible(self, project):
        project.set_visible(project.creator, False, save=True)
        project.reload()
        assert project.creator._id not in project.visible_contributor_ids
        assert project.creator not in project.visible_contributors
        assert project.logs.latest().action == NodeLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_make_visible(self, project, user2):
        project.set_visible(project.creator, False, save=True)
        project.set_visible(project.creator, True, save=True)
        project.reload()
        assert project.creator._id in project.visible_contributor_ids
        assert project.creator in project.visible_contributors
        assert project.logs.latest().action == NodeLog.MADE_CONTRIBUTOR_VISIBLE
        # Regression test: Ensure that hiding and showing the first contributor
        # does not change the visible contributor order
        assert list(project.visible_contributors) == [project.creator, user2]

    def test_set_visible_missing(self, project):
        with pytest.raises(ValueError):
            project.set_visible(UserFactory(), True)


class TestPermissionMethods:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    def test_has_permission(self, node):
        user = UserFactory()
        contributor = Contributor.objects.create(
            node=node, user=user,
            read=True, write=False, admin=False
        )

        assert node.has_permission(user, permissions.READ) is True
        assert node.has_permission(user, permissions.WRITE) is False
        assert node.has_permission(user, permissions.ADMIN) is False

        contributor.write = True
        contributor.save()
        assert node.has_permission(user, permissions.WRITE) is True

    def test_has_permission_passed_non_contributor_returns_false(self, node):
        noncontrib = UserFactory()
        assert node.has_permission(noncontrib, permissions.READ) is False

    def test_get_permissions(self, node):
        user = UserFactory()
        contributor = Contributor.objects.create(
            node=node, user=user,
            read=True, write=False, admin=False
        )
        assert node.get_permissions(user) == [permissions.READ]

        contributor.write = True
        contributor.save()
        assert node.get_permissions(user) == [permissions.READ, permissions.WRITE]

    def test_add_permission(self, node):
        user = UserFactory()
        Contributor.objects.create(
            node=node, user=user,
            read=True, write=False, admin=False
        )
        node.add_permission(user, permissions.WRITE)
        node.save()
        assert node.has_permission(user, permissions.WRITE) is True

    def test_remove_permission(self, node):
        assert node.has_permission(node.creator, permissions.ADMIN) is True
        assert node.has_permission(node.creator, permissions.WRITE) is True
        assert node.has_permission(node.creator, permissions.WRITE) is True
        node.remove_permission(node.creator, permissions.ADMIN)
        assert node.has_permission(node.creator, permissions.ADMIN) is False
        assert node.has_permission(node.creator, permissions.WRITE) is False
        assert node.has_permission(node.creator, permissions.WRITE) is False

    def test_remove_permission_not_granted(self, node, auth):
        contrib = UserFactory()
        node.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], auth=auth)
        with pytest.raises(ValueError):
            node.remove_permission(contrib, permissions.ADMIN)

    def test_set_permissions(self, node):
        low, high = UserFactory(), UserFactory()
        Contributor.objects.create(
            node=node, user=low,
            read=True, write=False, admin=False
        )
        Contributor.objects.create(
            node=node, user=high,
            read=True, write=True, admin=True
        )
        node.set_permissions(low, [permissions.READ, permissions.WRITE])
        assert node.has_permission(low, permissions.READ) is True
        assert node.has_permission(low, permissions.WRITE) is True
        assert node.has_permission(low, permissions.ADMIN) is False

        node.set_permissions(high, [permissions.READ, permissions.WRITE])
        assert node.has_permission(high, permissions.READ) is True
        assert node.has_permission(high, permissions.WRITE) is True
        assert node.has_permission(high, permissions.ADMIN) is False

    def test_set_permissions_raises_error_if_only_admins_permissions_are_reduced(self, node):
        # creator is the only admin
        with pytest.raises(NodeStateError) as excinfo:
            node.set_permissions(node.creator, permissions=[permissions.READ, permissions.WRITE])
        assert excinfo.value.args[0] == 'Must have at least one registered admin contributor'

    def test_add_permission_with_admin_also_grants_read_and_write(self, node):
        user = UserFactory()
        Contributor.objects.create(
            node=node, user=user,
            read=True, write=False, admin=False
        )
        node.add_permission(user, permissions.ADMIN)
        node.save()
        assert node.has_permission(user, permissions.ADMIN)
        assert node.has_permission(user, permissions.WRITE)

    def test_add_permission_already_granted(self, node):
        user = UserFactory()
        Contributor.objects.create(
            node=node, user=user,
            read=True, write=True, admin=True
        )
        with pytest.raises(ValueError):
            node.add_permission(user, permissions.ADMIN)

    def test_contributor_can_edit(self, node, auth):
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        node.add_contributor(
            contributor=contributor, auth=auth)
        node.save()
        assert bool(node.can_edit(contributor_auth)) is True
        assert bool(node.can_edit(other_guy_auth)) is False

    def test_can_edit_can_be_passed_a_user(self, user, node):
        assert bool(node.can_edit(user=user)) is True

    def test_creator_can_edit(self, auth, node):
        assert bool(node.can_edit(auth)) is True

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        user1_auth = Auth(user=user1)
        node = NodeFactory(is_public=True)
        # Noncontributor can't edit
        assert bool(node.can_edit(user1_auth)) is False

    def test_can_view_private(self, project, auth):
        # Create contributor and noncontributor
        link = PrivateLinkFactory()
        link.nodes.add(project)
        link.save()
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        project.add_contributor(
            contributor=contributor, auth=auth)
        project.save()
        # Only creator and contributor can view
        assert project.can_view(auth)
        assert project.can_view(contributor_auth)
        assert project.can_view(other_guy_auth) is False
        other_guy_auth.private_key = link.key
        assert project.can_view(other_guy_auth)
