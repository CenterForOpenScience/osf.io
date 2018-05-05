from osf_tests.factories import PreprintFactory, UserFactory, ProjectFactory, AuthUserFactory, NodeFactory
from osf.models.contributor import PreprintContributor
import mock
import pytest
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from api_tests.utils import disconnected_from_listeners
from osf.exceptions import ValidationError, NodeStateError
from .utils import capture_signals
from website.project.signals import contributor_added, contributor_removed
from osf.utils import permissions
from osf.utils.permissions import (
    ADMIN, DEFAULT_CONTRIBUTOR_PERMISSIONS, READ, WRITE
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def preprint(user):
    return PreprintFactory(creator=user)

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)

class TestPreprintContributors:
    def test_creator_is_added_as_contributor(self, fake):
        user = UserFactory()
        preprint = PreprintFactory(
            title=fake.bs(),
            creator=user
        )
        preprint.save()
        assert preprint.is_contributor(user) is True
        contributor = PreprintContributor.objects.get(user=user, preprint=preprint)
        assert contributor.visible is True
        assert contributor.read is True
        assert contributor.write is True
        assert contributor.admin is True


# Copied from tests/test_models.py
class TestContributorMethods:
    def test_add_contributor(self, preprint, user, auth):
        # A user is added as a contributor
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, auth=auth)
        preprint.save()
        assert preprint.is_contributor(user2) is True
        # last_log = preprint.logs.all().order_by('-date')[0]   # TODO: requires working logs
        # assert last_log.action == 'contributor_added'
        # assert last_log.params['contributors'] == [user2._id]

        assert user2 in user.recently_added.all()

    def test_add_contributors(self, preprint, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        preprint.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write', 'admin'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': False}
            ],
            auth=auth
        )
        # last_log = preprint.logs.all().order_by('-date')[0]
        # assert (
        #     last_log.params['contributors'] ==
        #     [user1._id, user2._id]
        # )
        assert preprint.is_contributor(user1)
        assert preprint.is_contributor(user2)
        assert user1._id in preprint.visible_contributor_ids
        assert user2._id not in preprint.visible_contributor_ids
        assert preprint.get_permissions(user1) == [permissions.READ, permissions.WRITE, permissions.ADMIN]
        assert preprint.get_permissions(user2) == [permissions.READ, permissions.WRITE]
        # last_log = preprint.logs.all().order_by('-date')[0]  # TODO: requires working logs
        # assert (
        #     last_log.params['contributors'] ==
        #     [user1._id, user2._id]
        # )

    def test_cant_add_creator_as_contributor_twice(self, preprint, user):
        preprint.add_contributor(contributor=user)
        preprint.save()
        assert len(preprint.contributors) == 1

    def test_cant_add_same_contributor_twice(self, preprint):
        contrib = UserFactory()
        preprint.add_contributor(contributor=contrib)
        preprint.save()
        preprint.add_contributor(contributor=contrib)
        preprint.save()
        assert len(preprint.contributors) == 2

    def test_remove_unregistered_conributor_removes_unclaimed_record(self, preprint, auth):
        new_user = preprint.add_unregistered_contributor(fullname='David Davidson',
            email='david@davidson.com', auth=auth)
        preprint.save()
        assert preprint.is_contributor(new_user)  # sanity check
        assert preprint._primary_key in new_user.unclaimed_records
        preprint.remove_contributor(
            auth=auth,
            contributor=new_user
        )
        preprint.save()
        new_user.refresh_from_db()
        assert preprint._primary_key not in new_user.unclaimed_records

    def test_is_contributor(self, preprint):
        contrib, noncontrib = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint)

        assert preprint.is_contributor(contrib) is True
        assert preprint.is_contributor(noncontrib) is False
        assert preprint.is_contributor(None) is False

    def test_visible_contributor_ids(self, preprint, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        PreprintContributor.objects.create(user=visible_contrib, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible_contrib, preprint=preprint, visible=False)
        assert visible_contrib._id in preprint.visible_contributor_ids
        assert invisible_contrib._id not in preprint.visible_contributor_ids

    def test_visible_contributors(self, preprint, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        PreprintContributor.objects.create(user=visible_contrib, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible_contrib, preprint=preprint, visible=False)
        assert visible_contrib in preprint.visible_contributors
        assert invisible_contrib not in preprint.visible_contributors

    def test_set_visible_false(self, preprint, auth):
        contrib = UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint, visible=True)
        preprint.set_visible(contrib, visible=False, auth=auth)
        preprint.save()
        assert PreprintContributor.objects.filter(user=contrib, preprint=preprint, visible=False).exists() is True

        # last_log = preprint.logs.all().order_by('-date')[0]  # TODO: add back in for logging
        # assert last_log.user == auth.user
        # assert last_log.action == PreprintLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_set_visible_true(self, preprint, auth):
        contrib = UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint, visible=False)
        preprint.set_visible(contrib, visible=True, auth=auth)
        preprint.save()
        assert PreprintContributor.objects.filter(user=contrib, preprint=preprint, visible=True).exists() is True

        # last_log = preprint.logs.all().order_by('-date')[0]  # TODO: add back in for logging
        # assert last_log.user == auth.user
        # assert last_log.action == PreprintLog.MADE_CONTRIBUTOR_VISIBLE

    # def test_set_visible_is_noop_if_visibility_is_unchanged(self, preprint, auth):  # TODO: uncomment when logging is added
    #     visible, invisible = UserFactory(), UserFactory()
    #     PreprintContributor.objects.create(user=visible, preprint=preprint, visible=True)
    #     PreprintContributor.objects.create(user=invisible, preprint=preprint, visible=False)
    #     original_log_count = preprint.logs.count()
    #     preprint.set_visible(invisible, visible=False, auth=auth)
    #     preprint.set_visible(visible, visible=True, auth=auth)
    #     preprint.save()
    #     assert preprint.logs.count() == original_log_count

    def test_set_visible_contributor_with_only_one_contributor(self, preprint, user):
        with pytest.raises(ValueError) as excinfo:
            preprint.set_visible(user=user, visible=False, auth=None)
        assert excinfo.value.message == 'Must have at least one visible contributor'

    def test_set_visible_missing(self, preprint):
        with pytest.raises(ValueError):
            preprint.set_visible(UserFactory(), True)

    def test_copy_contributors_from_adds_contributors(self, preprint):
        contrib, contrib2 = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=contrib, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=contrib2, preprint=preprint, visible=False)

        preprint2 = PreprintFactory()
        preprint2.copy_contributors_from(preprint)

        assert preprint2.is_contributor(contrib)
        assert preprint2.is_contributor(contrib2)

        assert preprint.is_contributor(contrib)
        assert preprint.is_contributor(contrib2)

    def test_copy_contributors_from_preserves_visibility(self, preprint):
        visible, invisible = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=visible, preprint=preprint, visible=True)
        PreprintContributor.objects.create(user=invisible, preprint=preprint, visible=False)

        preprint2 = PreprintFactory()
        preprint2.copy_contributors_from(preprint)

        assert PreprintContributor.objects.get(preprint=preprint, user=visible).visible is True
        assert PreprintContributor.objects.get(preprint=preprint, user=invisible).visible is False

    def test_copy_contributors_from_preserves_permissions(self, preprint):
        read, admin = UserFactory(), UserFactory()
        PreprintContributor.objects.create(user=read, preprint=preprint, read=True, write=False, admin=False)
        PreprintContributor.objects.create(user=admin, preprint=preprint, read=True, write=True, admin=True)

        preprint2 = PreprintFactory()
        preprint2.copy_contributors_from(preprint)

        assert preprint2.has_permission(read, 'read') is True
        assert preprint2.has_permission(read, 'write') is False
        assert preprint2.has_permission(admin, 'admin') is True

    def test_remove_contributor(self, preprint, auth):
        # A user is added as a contributor
        user2 = UserFactory()
        preprint.add_contributor(contributor=user2, auth=auth, save=True)
        assert user2 in preprint.contributors
        # The user is removed
        with disconnected_from_listeners(contributor_removed):
            preprint.remove_contributor(auth=auth, contributor=user2)
        preprint.reload()

        assert user2 not in preprint.contributors
        assert preprint.get_permissions(user2) == []
        assert preprint.logs.latest().action == 'contributor_removed'
        assert preprint.logs.latest().params['contributors'] == [user2._id]

    def test_remove_contributors(self, preprint, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        preprint.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': True}
            ],
            auth=auth
        )
        assert user1 in preprint.contributors
        assert user2 in preprint.contributors

        with disconnected_from_listeners(contributor_removed):
            preprint.remove_contributors(auth=auth, contributors=[user1, user2], save=True)
        preprint.reload()

        assert user1 not in preprint.contributors
        assert user2 not in preprint.contributors
        assert preprint.get_permissions(user1) == []
        assert preprint.get_permissions(user2) == []
        assert preprint.logs.latest().action == 'contributor_removed'

    def test_replace_contributor(self, preprint):
        contrib = UserFactory()
        preprint.add_contributor(contrib, auth=Auth(preprint.creator))
        preprint.save()
        assert contrib in preprint.contributors.all()  # sanity check
        replacer = UserFactory()
        old_length = preprint.contributors.count()
        preprint.replace_contributor(contrib, replacer)
        preprint.save()
        new_length = preprint.contributors.count()
        assert contrib not in preprint.contributors.all()
        assert replacer in preprint.contributors.all()
        assert old_length == new_length

        # test unclaimed_records is removed
        assert (
            preprint._id not in
            contrib.unclaimed_records.keys()
        )

    def test_permission_override_fails_if_no_admins(self, preprint, user):
        # User has admin permissions because they are the creator
        # Cannot lower permissions
        with pytest.raises(NodeStateError):
            preprint.add_contributor(user, permissions=['read', 'write'])

    def test_update_contributor(self, preprint, auth):
        new_contrib = AuthUserFactory()
        preprint.add_contributor(new_contrib, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS, auth=auth)

        assert preprint.get_permissions(new_contrib) == DEFAULT_CONTRIBUTOR_PERMISSIONS
        assert preprint.get_visible(new_contrib) is True

        preprint.update_contributor(
            new_contrib,
            READ,
            False,
            auth=auth
        )
        assert preprint.get_permissions(new_contrib) == [READ]
        assert preprint.get_visible(new_contrib) is False

    def test_update_contributor_non_admin_raises_error(self, preprint, auth):
        non_admin = AuthUserFactory()
        preprint.add_contributor(
            non_admin,
            permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS,
            auth=auth
        )
        with pytest.raises(PermissionsError):
            preprint.update_contributor(
                non_admin,
                None,
                False,
                auth=Auth(non_admin)
            )

    def test_update_contributor_only_admin_raises_error(self, preprint, auth):
        with pytest.raises(NodeStateError):
            preprint.update_contributor(
                auth.user,
                WRITE,
                True,
                auth=auth
            )

    def test_update_contributor_non_contrib_raises_error(self, preprint, auth):
        non_contrib = AuthUserFactory()
        with pytest.raises(ValueError):
            preprint.update_contributor(
                non_contrib,
                ADMIN,
                True,
                auth=auth
            )


# Copied from tests/test_models.py
class TestPreprintAddContributorRegisteredOrNot:

    def test_add_contributor_user_id(self, user, preprint):
        registered_user = UserFactory()
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), user_id=registered_user._id, save=True)
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is True

    def test_add_contributor_user_id_already_contributor(self, user, preprint):
        with pytest.raises(ValidationError) as excinfo:
            preprint.add_contributor_registered_or_not(auth=Auth(user), user_id=user._id, save=True)
        assert 'is already a contributor' in excinfo.value.message

    def test_add_contributor_invalid_user_id(self, user, preprint):
        with pytest.raises(ValueError) as excinfo:
            preprint.add_contributor_registered_or_not(auth=Auth(user), user_id='abcde', save=True)
        assert 'was not found' in excinfo.value.message

    def test_add_contributor_fullname_email(self, user, preprint):
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe', email='jane@doe.com')
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname(self, user, preprint):
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe')
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname_email_already_exists(self, user, preprint):
        registered_user = UserFactory()
        contributor_obj = preprint.add_contributor_registered_or_not(auth=Auth(user), full_name='F Mercury', email=registered_user.username)
        contributor = contributor_obj.user
        assert contributor in preprint.contributors
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
    def test_add_contributors_sends_contributor_added_signal(self, mock_send_mail, preprint, auth):
        user = UserFactory()
        contributors = [{
            'user': user,
            'visible': True,
            'permissions': ['read', 'write']
        }]
        with capture_signals() as mock_signals:
            preprint.add_contributors(contributors=contributors, auth=auth)
            preprint.save()
            assert preprint.is_contributor(user)
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
        # assert project.logs.latest().action == PreprintLog.MADE_CONTRIBUTOR_INVISIBLE  # TODO: add back in for logging

    def test_make_visible(self, project, user2):
        project.set_visible(project.creator, False, save=True)
        project.set_visible(project.creator, True, save=True)
        project.reload()
        assert project.creator._id in project.visible_contributor_ids
        assert project.creator in project.visible_contributors
        # assert project.logs.latest().action == PreprintLog.MADE_CONTRIBUTOR_VISIBLE  #
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

    def test_has_permission(self, preprint):
        user = UserFactory()
        contributor = PreprintContributor.objects.create(
            preprint=preprint, user=user,
            read=True, write=False, admin=False
        )

        assert preprint.has_permission(user, permissions.READ) is True
        assert preprint.has_permission(user, permissions.WRITE) is False
        assert preprint.has_permission(user, permissions.ADMIN) is False

        contributor.write = True
        contributor.save()
        assert preprint.has_permission(user, permissions.WRITE) is True

    def test_has_permission_passed_non_contributor_returns_false(self, preprint):
        noncontrib = UserFactory()
        assert preprint.has_permission(noncontrib, permissions.READ) is False

    def test_get_permissions(self, preprint):
        user = UserFactory()
        contributor = PreprintContributor.objects.create(
            preprint=preprint, user=user,
            read=True, write=False, admin=False
        )
        assert preprint.get_permissions(user) == [permissions.READ]

        contributor.write = True
        contributor.save()
        assert preprint.get_permissions(user) == [permissions.READ, permissions.WRITE]

    def test_add_permission(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user,
            read=True, write=False, admin=False
        )
        preprint.add_permission(user, permissions.WRITE)
        preprint.save()
        assert preprint.has_permission(user, permissions.WRITE) is True

    def test_remove_permission(self, preprint):
        assert preprint.has_permission(preprint.creator, permissions.ADMIN) is True
        assert preprint.has_permission(preprint.creator, permissions.WRITE) is True
        assert preprint.has_permission(preprint.creator, permissions.WRITE) is True
        preprint.remove_permission(preprint.creator, permissions.ADMIN)
        assert preprint.has_permission(preprint.creator, permissions.ADMIN) is False
        assert preprint.has_permission(preprint.creator, permissions.WRITE) is False
        assert preprint.has_permission(preprint.creator, permissions.WRITE) is False

    def test_remove_permission_not_granted(self, preprint, auth):
        contrib = UserFactory()
        preprint.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], auth=auth)
        with pytest.raises(ValueError):
            preprint.remove_permission(contrib, permissions.ADMIN)

    def test_set_permissions(self, preprint):
        low, high = UserFactory(), UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=low,
            read=True, write=False, admin=False
        )
        PreprintContributor.objects.create(
            preprint=preprint, user=high,
            read=True, write=True, admin=True
        )
        preprint.set_permissions(low, [permissions.READ, permissions.WRITE])
        assert preprint.has_permission(low, permissions.READ) is True
        assert preprint.has_permission(low, permissions.WRITE) is True
        assert preprint.has_permission(low, permissions.ADMIN) is False

        preprint.set_permissions(high, [permissions.READ, permissions.WRITE])
        assert preprint.has_permission(high, permissions.READ) is True
        assert preprint.has_permission(high, permissions.WRITE) is True
        assert preprint.has_permission(high, permissions.ADMIN) is False

    def test_set_permissions_raises_error_if_only_admins_permissions_are_reduced(self, preprint):
        # creator is the only admin
        with pytest.raises(NodeStateError) as excinfo:
            preprint.set_permissions(preprint.creator, permissions=[permissions.READ, permissions.WRITE])
        assert excinfo.value.args[0] == 'Must have at least one registered admin contributor'

    def test_add_permission_with_admin_also_grants_read_and_write(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user,
            read=True, write=False, admin=False
        )
        preprint.add_permission(user, permissions.ADMIN)
        preprint.save()
        assert preprint.has_permission(user, permissions.ADMIN)
        assert preprint.has_permission(user, permissions.WRITE)

    def test_add_permission_already_granted(self, preprint):
        user = UserFactory()
        PreprintContributor.objects.create(
            preprint=preprint, user=user
        )
        preprint.set_permissions(user, 'admin', validate=False)
        with pytest.raises(ValueError):
            preprint.add_permission(user, 'admin')

    def test_contributor_can_edit(self, preprint, auth):
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        preprint.add_contributor(
            contributor=contributor, auth=auth)
        preprint.save()
        assert bool(preprint.can_edit(contributor_auth)) is True
        assert bool(preprint.can_edit(other_guy_auth)) is False

    def test_can_edit_can_be_passed_a_user(self, user, preprint):
        assert bool(preprint.can_edit(user=user)) is True

    def test_creator_can_edit(self, auth, preprint):
        assert bool(preprint.can_edit(auth)) is True

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        user1_auth = Auth(user=user1)
        preprint = PreprintFactory(is_public=True)
        # Noncontributor can't edit
        assert bool(preprint.can_edit(user1_auth)) is False
