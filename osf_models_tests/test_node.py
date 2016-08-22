import datetime

from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from modularodm import Q
from modularodm.exceptions import ValidationError as MODMValidationError
import mock
import pytest
import pytz

from framework.exceptions import PermissionsError
from website.util.permissions import ADMIN
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
