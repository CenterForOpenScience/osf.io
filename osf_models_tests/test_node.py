import datetime

from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from modularodm import Q
from modularodm.exceptions import ValidationError as MODMValidationError
import mock
import pytest
import pytz

from framework.exceptions import PermissionsError
from website.util.permissions import READ, WRITE, ADMIN, expand_permissions
from website.project.signals import contributor_added
from website.exceptions import NodeStateError
from website.util import permissions

from osf_models.models import Node, Tag, NodeLog, Contributor, Sanction
from osf_models.exceptions import ValidationError
from osf_models.utils.auth import Auth

from .factories import ProjectFactory, NodeFactory, UserFactory, UnregUserFactory, RegistrationFactory, NodeLicenseRecordFactory
from .utils import capture_signals, assert_datetime_equal, mock_archive


@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)


@pytest.mark.django_db
def test_top_level_node_has_parent_node_none():
    project = ProjectFactory()
    assert project.parent_node is None

@pytest.mark.django_db
def test_component_has_parent_node():
    node = NodeFactory()
    assert type(node.parent_node) is Node


@pytest.mark.django_db
def test_license_searches_parent_nodes():
    license_record = NodeLicenseRecordFactory()
    project = ProjectFactory(node_license=license_record)
    node = NodeFactory(parent=project)
    assert project.license == license_record
    assert node.license == license_record

@pytest.mark.django_db
class TestNodeMODMCompat:

    def test_basic_querying(self):
        node_1 = ProjectFactory(is_public=False)
        node_2 = ProjectFactory(is_public=True)

        results = Node.find()
        assert len(results) == 2

        private = Node.find(Q('is_public', 'eq', False))
        assert node_1 in private
        assert node_2 not in private

    def test_compound_query(self):
        node = NodeFactory(is_public=True, title='foo')

        assert node in Node.find(Q('is_public', 'eq', True) & Q('title', 'eq', 'foo'))
        assert node not in Node.find(Q('is_public', 'eq', False) & Q('title', 'eq', 'foo'))

    def test_title_validation(self):
        node = NodeFactory.build(title='')
        with pytest.raises(MODMValidationError):
            node.save()
        with pytest.raises(DjangoValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['This field cannot be blank.']}

        too_long = 'a' * 201
        node = NodeFactory.build(title=too_long)
        with pytest.raises(DjangoValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['Title cannot exceed 200 characters.']}

    def test_remove_one(self):
        node = ProjectFactory()
        node2 = ProjectFactory()
        assert len(Node.find()) == 2  # sanity check
        Node.remove_one(node)
        assert len(Node.find()) == 1
        assert node2 in Node.find()

    def test_querying_on_guid_id(self):
        node = NodeFactory()
        assert len(node._id) == 5
        assert node in Node.find(Q('_id', 'eq', node._id))

@pytest.mark.django_db
class TestLogging:

    def test_add_log(self, node, auth):
        node.add_log(NodeLog.PROJECT_CREATED, params={'node': node._id}, auth=auth)
        node.add_log(NodeLog.EMBARGO_INITIATED, params={'node': node._id}, auth=auth)
        node.save()

        last_log = node.logs.first()
        assert last_log.action == NodeLog.EMBARGO_INITIATED
        # date is tzaware
        assert last_log.date.tzinfo == pytz.utc

        # updates node.date_modified
        assert_datetime_equal(node.date_modified, last_log.date)


@pytest.mark.django_db
class TestTagging:

    def test_add_tag(self, node, auth):
        node.add_tag('FoO', auth=auth)
        node.save()

        tag = Tag.objects.get(name='FoO')
        assert node.tags.count() == 1
        assert tag in node.tags.all()

        last_log = node.logs.all().order_by('-date')[0]
        assert last_log.action == NodeLog.TAG_ADDED
        assert last_log.params['tag'] == 'FoO'
        assert last_log.params['node'] == node._id

    def test_add_system_tag(self, node):
        original_log_count = node.logs.count()
        node.add_system_tag('FoO')
        node.save()

        tag = Tag.objects.get(name='FoO')
        assert node.tags.count() == 1
        assert tag in node.tags.all()

        assert tag.system is True

        # No log added
        new_log_count = node.logs.count()
        assert original_log_count == new_log_count

    def test_system_tags_property(self, node, auth):
        node.add_system_tag('FoO')
        node.add_tag('bAr', auth=auth)

        assert 'FoO' in node.system_tags
        assert 'bAr' not in node.system_tags

@pytest.mark.django_db
class TestSearch:

    @mock.patch('website.search.search.update_node')
    def test_update_search(self, mock_update_node, node):
        node.update_search()
        assert mock_update_node.called

@pytest.mark.django_db
class TestNodeCreation:

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

    def test_project_created_log_is_added(self, fake):
        user = UserFactory()
        node = Node(
            title=fake.bs(),
            creator=user
        )
        node.save()
        assert node.logs.count() == 1
        first_log = node.logs.first()
        assert first_log.action == NodeLog.PROJECT_CREATED
        params = first_log.params
        assert params['node'] == node._id
        assert_datetime_equal(first_log.date, node.date_created)

# Copied from tests/test_models.py
@pytest.mark.django_db
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

    def test_is_contributor(self, node):
        contrib, noncontrib = UserFactory(), UserFactory()
        Contributor.objects.create(user=contrib, node=node)

        assert node.is_contributor(contrib) is True
        assert node.is_contributor(noncontrib) is False

    def test_visible_contributor_ids(self, node, user):
        visible_contrib = UserFactory()
        invisible_contrib = UserFactory()
        Contributor.objects.create(user=visible_contrib, node=node, visible=True)
        Contributor.objects.create(user=invisible_contrib, node=node, visible=False)
        assert visible_contrib._id in node.visible_contributor_ids
        assert invisible_contrib._id not in node.visible_contributor_ids

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

@pytest.mark.django_db
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

@pytest.mark.django_db
class TestPermissionMethods:

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

# Copied from tests/test_models.py
@pytest.mark.django_db
class TestAddUnregisteredContributor:

    def test_add_unregistered_contributor(self, node, user, auth):
        node.add_unregistered_contributor(
            email='foo@bar.com',
            fullname='Weezy F. Baby',
            auth=auth
        )
        node.save()
        latest_contributor = Contributor.objects.get(node=node, user__username='foo@bar.com').user
        assert latest_contributor.username == 'foo@bar.com'
        assert latest_contributor.fullname == 'Weezy F. Baby'
        assert bool(latest_contributor.is_registered) is False

        # A log event was added
        assert node.logs.first().action == 'contributor_added'
        assert node._id in latest_contributor.unclaimed_records, 'unclaimed record was added'
        unclaimed_data = latest_contributor.get_unclaimed_record(node._primary_key)
        assert unclaimed_data['referrer_id'] == user._primary_key
        assert bool(node.is_contributor(latest_contributor)) is True
        assert unclaimed_data['email'] == 'foo@bar.com'

    def test_add_unregistered_adds_new_unclaimed_record_if_user_already_in_db(self, fake, node, auth):
        user = UnregUserFactory()
        given_name = fake.name()
        new_user = node.add_unregistered_contributor(
            email=user.username,
            fullname=given_name,
            auth=auth
        )
        node.save()
        # new unclaimed record was added
        assert node._primary_key in new_user.unclaimed_records
        unclaimed_data = new_user.get_unclaimed_record(node._primary_key)
        assert unclaimed_data['name'] == given_name

    def test_add_unregistered_raises_error_if_user_is_registered(self, node, auth):
        user = UserFactory(is_registered=True)  # A registered user
        with pytest.raises(ValidationError):
            node.add_unregistered_contributor(
                email=user.username,
                fullname=user.fullname,
                auth=auth
            )

@pytest.mark.django_db
def test_find_for_user():
    node1, node2 = NodeFactory(is_public=False), NodeFactory(is_public=True)
    contrib = UserFactory()
    noncontrib = UserFactory()
    Contributor.objects.create(node=node1, user=contrib)
    Contributor.objects.create(node=node2, user=contrib)
    assert node1 in Node.find_for_user(contrib)
    assert node2 in Node.find_for_user(contrib)
    assert node1 not in Node.find_for_user(noncontrib)

    assert node1 in Node.find_for_user(contrib, Q('is_public', 'eq', False))
    assert node2 not in Node.find_for_user(contrib, Q('is_public', 'eq', False))


@pytest.mark.django_db
def test_can_comment():
    contrib = UserFactory()
    public_node = NodeFactory(is_public=True)
    Contributor.objects.create(node=public_node, user=contrib)
    assert public_node.can_comment(Auth(contrib)) is True
    noncontrib = UserFactory()
    assert public_node.can_comment(Auth(noncontrib)) is True

    private_node = NodeFactory(is_public=False, public_comments=False)
    Contributor.objects.create(node=private_node, user=contrib, read=True)
    assert private_node.can_comment(Auth(contrib)) is True
    noncontrib = UserFactory()
    assert private_node.can_comment(Auth(noncontrib)) is False


@pytest.mark.django_db
def test_parent_kwarg():
    parent = NodeFactory()
    child = NodeFactory(parent=parent)
    assert child.parent_node == parent
    assert child in parent.nodes.all()


@pytest.mark.django_db
class TestSetPrivacy:

    def test_set_privacy_checks_admin_permissions(self, user):
        non_contrib = UserFactory()
        project = ProjectFactory(creator=user, is_public=False)
        # Non-contrib can't make project public
        with pytest.raises(PermissionsError):
            project.set_privacy('public', Auth(non_contrib))

        project.set_privacy('public', Auth(project.creator))
        project.save()

        # Non-contrib can't make project private
        with pytest.raises(PermissionsError):
            project.set_privacy('private', Auth(non_contrib))

    def test_set_privacy_pending_embargo(self, user):
        project = ProjectFactory(creator=user, is_public=False)
        with mock_archive(project, embargo=True, autocomplete=True) as registration:
            assert bool(registration.embargo.is_pending_approval) is True
            assert bool(registration.is_pending_embargo) is True
            with pytest.raises(NodeStateError):
                registration.set_privacy('public', Auth(project.creator))

    def test_set_privacy_pending_registration(self, user):
        project = ProjectFactory(creator=user, is_public=False)
        with mock_archive(project, embargo=False, autocomplete=True) as registration:
            assert bool(registration.registration_approval.is_pending_approval) is True
            assert bool(registration.is_pending_registration) is True
            with pytest.raises(NodeStateError):
                registration.set_privacy('public', Auth(project.creator))

    def test_set_privacy(self, node, auth):
        node.set_privacy('public', auth=auth)
        node.save()
        assert bool(node.is_public) is True
        assert node.logs.first().action == NodeLog.MADE_PUBLIC
        assert node.keenio_read_key != ''
        node.set_privacy('private', auth=auth)
        node.save()
        assert bool(node.is_public) is False
        assert node.logs.first().action == NodeLog.MADE_PRIVATE
        assert node.keenio_read_key == ''

    @mock.patch('website.mails.queue_mail')
    def test_set_privacy_sends_mail_default(self, mock_queue, node, auth):
        node.set_privacy('private', auth=auth)
        node.set_privacy('public', auth=auth)
        assert mock_queue.call_count == 1

    @mock.patch('website.mails.queue_mail')
    def test_set_privacy_sends_mail(self, mock_queue, node, auth):
        node.set_privacy('private', auth=auth)
        node.set_privacy('public', auth=auth, meeting_creation=False)
        assert mock_queue.call_count == 1

    @mock.patch('osf_models.models.queued_mail.queue_mail')
    def test_set_privacy_skips_mail_if_meeting(self, mock_queue, node, auth):
        node.set_privacy('private', auth=auth)
        node.set_privacy('public', auth=auth, meeting_creation=True)
        assert bool(mock_queue.called) is False

    def test_set_privacy_can_not_cancel_pending_embargo_for_registration(self, node, user, auth):
        registration = RegistrationFactory(project=node)
        registration.embargo_registration(
            user,
            timezone.now() + datetime.timedelta(days=10)
        )
        assert bool(registration.is_pending_embargo) is True

        with pytest.raises(NodeStateError):
            registration.set_privacy('public', auth=auth)
        assert bool(registration.is_public) is False

    def test_set_privacy_requests_embargo_termination_on_embargoed_registration(self, node, user, auth):
        for i in range(3):
            c = UserFactory()
            node.add_contributor(c, [ADMIN])
        registration = RegistrationFactory(project=node)
        registration.embargo_registration(
            user,
            timezone.now() + datetime.timedelta(days=10)
        )
        assert len([a for a in registration.get_admin_contributors_recursive(unique_users=True)]) == 4
        embargo = registration.embargo
        embargo.state = Sanction.APPROVED
        embargo.save()
        with mock.patch('osf_models.models.Registration.request_embargo_termination') as mock_request_embargo_termination:
            registration.set_privacy('public', auth=auth)
            assert mock_request_embargo_termination.call_count == 1


# copied from tests/test_models.py
@pytest.mark.django_db
class TestManageContributors:

    def test_contributor_manage_visibility(self, node, user, auth):
        reg_user1 = UserFactory()
        #This makes sure manage_contributors uses set_visible so visibility for contributors is added before visibility
        #for other contributors is removed ensuring there is always at least one visible contributor
        node.add_contributor(contributor=user, permissions=['read', 'write', 'admin'], auth=auth)
        node.add_contributor(contributor=reg_user1, permissions=['read', 'write', 'admin'], auth=auth)

        node.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': 'admin', 'visible': True},
                {'id': reg_user1._id, 'permission': 'admin', 'visible': False},
            ],
            auth=auth,
            save=True
        )
        node.manage_contributors(
            user_dicts=[
                {'id': user._id, 'permission': 'admin', 'visible': False},
                {'id': reg_user1._id, 'permission': 'admin', 'visible': True},
            ],
            auth=auth,
            save=True
        )

        assert len(node.visible_contributor_ids) == 1

    def test_manage_contributors_cannot_remove_last_admin_contributor(self, auth, node):
        user2 = UserFactory()
        node.add_contributor(contributor=user2, permissions=[READ, WRITE], auth=auth)
        node.save()
        with pytest.raises(NodeStateError) as excinfo:
            node.manage_contributors(
                user_dicts=[{'id': user2._id,
                             'permission': WRITE,
                             'visible': True}],
                auth=auth,
                save=True
            )
        assert excinfo.value.args[0] == 'Must have at least one registered admin contributor'

    @pytest.mark.skip('Contributor reordering not yet implemented')
    def test_manage_contributors_logs_when_users_reorder(self, node, user, auth):
        user2 = UserFactory()
        node.add_contributor(contributor=user2, permissions=[READ, WRITE], auth=auth)
        node.save()
        node.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permission': WRITE,
                    'visible': True,
                },
                {
                    'id': user._id,
                    'permission': ADMIN,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        latest_log = node.logs.latest()
        assert latest_log.action == NodeLog.CONTRIB_REORDERED
        assert latest_log.user == user
        assert user._id in latest_log.params['contributors']
        assert user2._id in latest_log.params['contributors']

    def test_manage_contributors_new_contributor(self, node, auth):
        user = UserFactory()
        users = [
            {'id': user._id, 'permission': READ, 'visible': True},
            {'id': node.creator._id, 'permission': [READ, WRITE, ADMIN], 'visible': True},
        ]
        with pytest.raises(ValueError) as excinfo:
            node.manage_contributors(
                users, auth=auth, save=True
            )
        assert excinfo.value.args[0] == 'User {0} not in contributors'.format(user.fullname)

    def test_manage_contributors_no_contributors(self, node, auth):
        with pytest.raises(NodeStateError):
            node.manage_contributors(
                [], auth=auth, save=True,
            )

    def test_manage_contributors_no_admins(self, node):
        user = UserFactory()
        node.add_contributor(
            user,
            permissions=[READ, WRITE, ADMIN],
            save=True
        )
        users = [
            {'id': node.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with pytest.raises(NodeStateError):
            node.manage_contributors(
                users, auth=auth, save=True,
            )

    def test_manage_contributors_no_registered_admins(self, node, auth):
        unregistered = UnregUserFactory()
        node.add_contributor(
            unregistered,
            permissions=['read', 'write', 'admin'],
            save=True
        )
        users = [
            {'id': node.creator._id, 'permission': READ, 'visible': True},
            {'id': unregistered._id, 'permission': ADMIN, 'visible': True},
        ]
        with pytest.raises(NodeStateError):
            node.manage_contributors(
                users, auth=auth, save=True,
            )

@pytest.mark.django_db
def test_get_admin_contributors(user, auth):
    read, write, admin = UserFactory(), UserFactory(), UserFactory()
    nonactive_admin = UserFactory()
    noncontrib = UserFactory()
    project = ProjectFactory(creator=user)
    project.add_contributor(read, auth=auth, permissions=[READ])
    project.add_contributor(write, auth=auth, permissions=expand_permissions(WRITE))
    project.add_contributor(admin, auth=auth, permissions=expand_permissions(ADMIN))
    project.add_contributor(nonactive_admin, auth=auth, permissions=expand_permissions(ADMIN))
    project.save()

    nonactive_admin.is_disabled = True
    nonactive_admin.save()

    result = list(project.get_admin_contributors([
        read, write, admin, noncontrib, nonactive_admin
    ]))

    assert admin in result
    assert read not in result
    assert write not in result
    assert noncontrib not in result
    assert nonactive_admin not in result

# copied from tests/test_models.py
@pytest.mark.django_db
class TestNodeTraversals:

    @pytest.fixture()
    def viewer(self):
        return UserFactory()

    @pytest.fixture()
    def root(self, user):
        return ProjectFactory(creator=user)

    def test_next_descendants(self, root, user, viewer, auth):
        comp1 = ProjectFactory(creator=user, parent=root)
        comp1a = ProjectFactory(creator=user, parent=comp1)
        comp1a.add_contributor(viewer, auth=auth, permissions=['read'])
        ProjectFactory(creator=user, parent=comp1)
        comp2 = ProjectFactory(creator=user, parent=root)
        comp2.add_contributor(viewer, auth=auth, permissions=['read'])
        comp2a = ProjectFactory(creator=user, parent=comp2)
        comp2a.add_contributor(viewer, auth=auth, permissions=['read'])
        ProjectFactory(creator=user, parent=comp2)

        descendants = root.next_descendants(
            Auth(viewer),
            condition=lambda auth, node: node.is_contributor(auth.user)
        )
        assert len(descendants) == 2  # two immediate children
        assert len(descendants[0][1]) == 1  # only one visible child of comp1
        assert len(descendants[1][1]) == 0  # don't auto-include comp2's children

    @mock.patch('osf_models.models.node.AbstractNode.update_search')
    def test_delete_registration_tree(self, mock_update_search):
        proj = NodeFactory()
        NodeFactory(parent=proj)
        comp2 = NodeFactory(parent=proj)
        NodeFactory(parent=comp2)
        reg = RegistrationFactory(project=proj)
        reg_ids = [reg._id] + [r._id for r in reg.get_descendants_recursive()]
        reg.delete_registration_tree(save=True)
        assert Node.find(Q('_id', 'in', reg_ids) & Q('is_deleted', 'eq', False)).count() == 0
        assert mock_update_search.call_count == len(reg_ids)

    @mock.patch('osf_models.models.node.AbstractNode.update_search')
    def test_delete_registration_tree_deletes_backrefs(self, mock_update_search):
        proj = NodeFactory()
        NodeFactory(parent=proj)
        comp2 = NodeFactory(parent=proj)
        NodeFactory(parent=comp2)
        reg = RegistrationFactory(project=proj)
        reg.delete_registration_tree(save=True)
        assert bool(proj.registrations_all) is False

    def test_get_active_contributors_recursive_with_duplicate_users(self, user, viewer, auth):
        parent = ProjectFactory(creator=user)

        child = ProjectFactory(creator=viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=auth,
                              permissions=expand_permissions(WRITE))
        grandchild = ProjectFactory(creator=user, parent=child)

        contributors = list(parent.get_active_contributors_recursive())
        assert len(contributors) == 4
        user_ids = [u._id for u, node in contributors]

        assert user._id in user_ids
        assert viewer._id in user_ids
        assert child_non_admin._id in user_ids

        node_ids = [node._id for u, node in contributors]
        assert parent._id in node_ids
        assert grandchild._id in node_ids

    def test_get_active_contributors_recursive_with_no_duplicate_users(self, user, viewer, auth):
        parent = ProjectFactory(creator=user)

        child = ProjectFactory(creator=viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=auth,
                              permissions=expand_permissions(WRITE))
        grandchild = ProjectFactory(creator=user, parent=child)  # noqa

        contributors = list(parent.get_active_contributors_recursive(unique_users=True))
        assert len(contributors) == 3
        user_ids = [u._id for u, node in contributors]

        assert user._id in user_ids
        assert viewer._id in user_ids
        assert child_non_admin._id in user_ids

        node_ids = [node._id for u, node in contributors]
        assert parent._id in node_ids

    def test_get_admin_contributors_recursive_with_duplicate_users(self, viewer, user, auth):
        parent = ProjectFactory(creator=user)

        child = ProjectFactory(creator=viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=auth,
                              permissions=expand_permissions(WRITE))
        child.save()

        grandchild = ProjectFactory(creator=user, parent=child)  # noqa

        admins = list(parent.get_admin_contributors_recursive())
        assert len(admins) == 3
        admin_ids = [u._id for u, node in admins]
        assert user._id in admin_ids
        assert viewer._id in admin_ids

        node_ids = [node._id for u, node in admins]
        assert parent._id in node_ids

    def test_get_admin_contributors_recursive_no_duplicates(self, user, viewer, auth):
        parent = ProjectFactory(creator=user)

        child = ProjectFactory(creator=viewer, parent=parent)
        child_non_admin = UserFactory()
        child.add_contributor(child_non_admin,
                              auth=auth,
                              permissions=expand_permissions(WRITE))
        child.save()

        grandchild = ProjectFactory(creator=user, parent=child)  # noqa

        admins = list(parent.get_admin_contributors_recursive(unique_users=True))
        assert len(admins) == 2
        admin_ids = [u._id for u, node in admins]
        assert user._id in admin_ids
        assert viewer._id in admin_ids

    def test_get_descendants_recursive(self, user, root, auth, viewer):
        comp1 = ProjectFactory(creator=user, parent=root)
        comp1a = ProjectFactory(creator=user, parent=comp1)
        comp1a.add_contributor(viewer, auth=auth, permissions='read')
        comp1b = ProjectFactory(creator=user, parent=comp1)
        comp2 = ProjectFactory(creator=user, parent=root)
        comp2.add_contributor(viewer, auth=auth, permissions='read')
        comp2a = ProjectFactory(creator=user, parent=comp2)
        comp2a.add_contributor(viewer, auth=auth, permissions='read')
        comp2b = ProjectFactory(creator=user, parent=comp2)

        descendants = root.get_descendants_recursive()
        ids = {d._id for d in descendants}
        assert bool({node._id for node in [comp1, comp1a, comp1b, comp2, comp2a, comp2b]}.difference(ids)) is False

    def test_get_descendants_recursive_filtered(self, user, root, viewer, auth):
        comp1 = ProjectFactory(creator=user, parent=root)
        comp1a = ProjectFactory(creator=user, parent=comp1)
        comp1a.add_contributor(viewer, auth=auth, permissions='read')
        ProjectFactory(creator=user, parent=comp1)
        comp2 = ProjectFactory(creator=user)
        comp2.add_contributor(viewer, auth=auth, permissions='read')
        comp2a = ProjectFactory(creator=user, parent=comp2)
        comp2a.add_contributor(viewer, auth=auth, permissions='read')
        ProjectFactory(creator=user, parent=comp2)

        descendants = root.get_descendants_recursive(
            lambda n: n.is_contributor(viewer)
        )
        ids = {d._id for d in descendants}
        nids = {node._id for node in [comp1a, comp2, comp2a]}
        assert bool(ids.difference(nids)) is False

    @pytest.mark.skip('Pointers not yet implemented')
    def test_get_descendants_recursive_cyclic(self, user, root, auth):
        point1 = ProjectFactory(creator=user, parent=root)
        point2 = ProjectFactory(creator=user, parent=root)
        point1.add_pointer(point2, auth=auth)
        point2.add_pointer(point1, auth=auth)

        descendants = list(point1.get_descendants_recursive())
        assert len(descendants) == 1
