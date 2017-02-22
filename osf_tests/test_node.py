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
from website.project.signals import contributor_added, contributor_removed, after_create_registration
from website.exceptions import NodeStateError
from website.util import permissions, disconnected_from_listeners
from website.citations.utils import datetime_to_csl
from website import language
from website.project.model import ensure_schemas

from osf.models import (
    AbstractNode,
    Node,
    Tag,
    NodeLog,
    Contributor,
    Sanction,
    NodeRelation,
    Registration,
    DraftRegistrationApproval,
)
from addons.wiki.models import NodeWikiPage
from osf.exceptions import ValidationError
from osf.utils.auth import Auth

from .factories import (
    ProjectFactory,
    NodeFactory,
    UserFactory,
    UnregUserFactory,
    RegistrationFactory,
    DraftRegistrationFactory,
    NodeLicenseRecordFactory,
    PrivateLinkFactory,
    CollectionFactory,
    NodeRelationFactory,
    InstitutionFactory,
)
from .factories import get_default_metaschema
from addons.wiki.tests.factories import NodeWikiFactory
from .utils import capture_signals, assert_datetime_equal, mock_archive

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)


def test_top_level_node_has_parent_node_none():
    project = ProjectFactory()
    assert project.parent_node is None

def test_component_has_parent_node():
    project = ProjectFactory()
    node = NodeFactory(parent=project)
    assert node.parent_node == project

def test_components_have_root():
    root = ProjectFactory()
    child = NodeFactory(parent=root)
    child1 = NodeFactory(parent=root)
    child2 = NodeFactory(parent=root)
    grandchild = NodeFactory(parent=child)
    grandchild1 = NodeFactory(parent=child)
    grandchild2 = NodeFactory(parent=child)
    grandchild3 = NodeFactory(parent=child)
    grandchild_1 = NodeFactory(parent=child1)
    grandchild1_1 = NodeFactory(parent=child1)
    grandchild2_1 = NodeFactory(parent=child1)
    grandchild3_1 = NodeFactory(parent=child1)
    grandchild_2 = NodeFactory(parent=child2)
    grandchild1_2 = NodeFactory(parent=child2)
    grandchild2_2 = NodeFactory(parent=child2)
    grandchild3_2 = NodeFactory(parent=child2)
    greatgrandchild = NodeFactory(parent=grandchild)
    greatgrandchild1 = NodeFactory(parent=grandchild1)
    greatgrandchild2 = NodeFactory(parent=grandchild2)
    greatgrandchild3 = NodeFactory(parent=grandchild3)
    greatgrandchild_1 = NodeFactory(parent=grandchild_1)

    assert child.root == root
    assert child1.root == root
    assert child2.root == root
    assert grandchild.root == root
    assert grandchild1.root == root
    assert grandchild2.root == root
    assert grandchild3.root == root
    assert grandchild_1.root == root
    assert grandchild1_1.root == root
    assert grandchild2_1.root == root
    assert grandchild3_1.root == root
    assert grandchild_2.root == root
    assert grandchild1_2.root == root
    assert grandchild2_2.root == root
    assert grandchild3_2.root == root
    assert greatgrandchild.root == root
    assert greatgrandchild1.root == root
    assert greatgrandchild2.root == root
    assert greatgrandchild3.root == root
    assert greatgrandchild_1.root == root

# https://openscience.atlassian.net/browse/OSF-7378
def test_root_for_linked_node_does_not_return_linking_parent():
    project = ProjectFactory(title='Project')
    root = ProjectFactory(title='Root')
    child = NodeFactory(title='Child', parent=root)

    project.add_node_link(root, auth=Auth(project.creator), save=True)
    assert root.root == root
    assert child.root == root

def test_get_children():
    root = ProjectFactory()
    child = NodeFactory(parent=root)
    child1 = NodeFactory(parent=root)
    child2 = NodeFactory(parent=root)
    grandchild = NodeFactory(parent=child)
    grandchild1 = NodeFactory(parent=child)
    grandchild2 = NodeFactory(parent=child)
    grandchild3 = NodeFactory(parent=child)
    grandchild_1 = NodeFactory(parent=child1)
    grandchild1_1 = NodeFactory(parent=child1)
    grandchild2_1 = NodeFactory(parent=child1)
    grandchild3_1 = NodeFactory(parent=child1)
    grandchild_2 = NodeFactory(parent=child2)
    grandchild1_2 = NodeFactory(parent=child2)
    grandchild2_2 = NodeFactory(parent=child2)
    grandchild3_2 = NodeFactory(parent=child2)
    greatgrandchild = NodeFactory(parent=grandchild)
    greatgrandchild1 = NodeFactory(parent=grandchild1)
    greatgrandchild2 = NodeFactory(parent=grandchild2)
    greatgrandchild3 = NodeFactory(parent=grandchild3)
    greatgrandchild_1 = NodeFactory(parent=grandchild_1)

    assert 20 == len(Node.objects.get_children(root))

def test_get_children_with_barren_parent():
    root = ProjectFactory()

    assert 0 == len(Node.objects.get_children(root))


def test_get_children_with_links():
    root = ProjectFactory()
    child = NodeFactory(parent=root)
    child1 = NodeFactory(parent=root)
    child2 = NodeFactory(parent=root)
    grandchild = NodeFactory(parent=child)
    grandchild1 = NodeFactory(parent=child)
    grandchild2 = NodeFactory(parent=child)
    grandchild3 = NodeFactory(parent=child)
    grandchild_1 = NodeFactory(parent=child1)
    grandchild1_1 = NodeFactory(parent=child1)
    grandchild2_1 = NodeFactory(parent=child1)
    grandchild3_1 = NodeFactory(parent=child1)
    grandchild_2 = NodeFactory(parent=child2)
    grandchild1_2 = NodeFactory(parent=child2)
    grandchild2_2 = NodeFactory(parent=child2)
    grandchild3_2 = NodeFactory(parent=child2)
    greatgrandchild = NodeFactory(parent=grandchild)
    greatgrandchild1 = NodeFactory(parent=grandchild1)
    greatgrandchild2 = NodeFactory(parent=grandchild2)
    greatgrandchild3 = NodeFactory(parent=grandchild3)
    greatgrandchild_1 = NodeFactory(parent=grandchild_1)

    child.add_node_link(root, auth=Auth(root.creator))
    child.add_node_link(greatgrandchild_1, auth=Auth(greatgrandchild_1.creator))
    greatgrandchild_1.add_node_link(child, auth=Auth(child.creator))

    assert 20 == len(Node.objects.get_children(root))

def test_get_roots():
    top_level1 = ProjectFactory(is_public=True)
    top_level2 = ProjectFactory(is_public=True)
    top_level_private = ProjectFactory(is_public=False)
    child1 = NodeFactory(parent=top_level1)
    child2 = NodeFactory(parent=top_level2)

    # top_level2 is linked to by another node
    node = NodeFactory(is_public=True)
    node.add_node_link(top_level2, auth=Auth(node.creator))

    results = AbstractNode.objects.get_roots()
    assert top_level1 in results
    assert top_level2 in results
    assert top_level_private in results
    assert child1 not in results
    assert child2 not in results

    public_results = AbstractNode.objects.filter(is_public=True).get_roots()
    assert top_level1 in public_results
    assert top_level2 in public_results
    assert top_level_private not in public_results
    assert child1 not in public_results
    assert child2 not in public_results

    public_results2 = AbstractNode.objects.get_roots().filter(is_public=True)
    assert top_level1 in public_results2
    assert top_level2 in public_results2
    assert top_level_private not in public_results2
    assert child1 not in public_results2
    assert child2 not in public_results2

def test_license_searches_parent_nodes():
    license_record = NodeLicenseRecordFactory()
    project = ProjectFactory(node_license=license_record)
    node = NodeFactory(parent=project)
    assert project.license == license_record
    assert node.license == license_record

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


# copied from tests/test_models.py
class TestProject:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user, description='foobar')

    def test_repr(self, project):
        assert project.title in repr(project)
        assert project._id in repr(project)

    def test_url(self, project):
        assert (
            project.url ==
            '/{0}/'.format(project._primary_key)
        )

    def test_api_url(self, project):
        api_url = project.api_url
        assert api_url == '/api/v1/project/{0}/'.format(project._primary_key)

    def test_parent_id(self, project):
        assert not project.parent_id

    def test_root_id_is_same_as_own_id_for_top_level_nodes(self, project):
        project.reload()
        assert project.root_id == project.id

    def test_nodes_active(self, project, auth):
        node = NodeFactory(parent=project)
        deleted_node = NodeFactory(parent=project, is_deleted=True)

        linked_node = NodeFactory()
        project.add_node_link(linked_node, auth=auth)
        deleted_linked_node = NodeFactory(is_deleted=True)
        project.add_node_link(deleted_linked_node, auth=auth)

        assert node in project.nodes_active
        assert deleted_node not in project.nodes_active

        assert linked_node in project.nodes_active
        assert deleted_linked_node not in project.nodes_active


class TestLogging:

    def test_add_log(self, node, auth):
        node.add_log(NodeLog.PROJECT_CREATED, params={'node': node._id}, auth=auth)
        node.add_log(NodeLog.EMBARGO_INITIATED, params={'node': node._id}, auth=auth)
        node.save()

        last_log = node.logs.latest()
        assert last_log.action == NodeLog.EMBARGO_INITIATED
        # date is tzaware
        assert last_log.date.tzinfo == pytz.utc

        # updates node.date_modified
        assert_datetime_equal(node.date_modified, last_log.date)


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

class TestSearch:

    @mock.patch('website.search.search.update_node')
    def test_update_search(self, mock_update_node, node):
        node.update_search()
        assert mock_update_node.called

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

# Copied from tests/test_models.py
class TestNodeAddContributorRegisteredOrNot:

    def test_add_contributor_user_id(self, user, node):
        registered_user = UserFactory()
        contributor = node.add_contributor_registered_or_not(auth=Auth(user), user_id=registered_user._id, save=True)
        assert contributor in node.contributors
        assert contributor.is_registered is True

    def test_add_contributor_user_id_already_contributor(self, user, node):
        with pytest.raises(MODMValidationError) as excinfo:
            node.add_contributor_registered_or_not(auth=Auth(user), user_id=user._id, save=True)
        assert 'is already a contributor' in excinfo.value.message

    def test_add_contributor_invalid_user_id(self, user, node):
        with pytest.raises(ValueError) as excinfo:
            node.add_contributor_registered_or_not(auth=Auth(user), user_id='abcde', save=True)
        assert 'was not found' in excinfo.value.message

    def test_add_contributor_fullname_email(self, user, node):
        contributor = node.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe', email='jane@doe.com')
        assert contributor in node.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname(self, user, node):
        contributor = node.add_contributor_registered_or_not(auth=Auth(user), full_name='Jane Doe')
        assert contributor in node.contributors
        assert contributor.is_registered is False

    def test_add_contributor_fullname_email_already_exists(self, user, node):
        registered_user = UserFactory()
        contributor = node.add_contributor_registered_or_not(auth=Auth(user), full_name='F Mercury', email=registered_user.username)
        assert contributor in node.contributors
        assert contributor.is_registered is True

class TestContributorProperties:

    def test_admin_contributors(self, user):
        project = ProjectFactory(creator=user)
        assert list(project.admin_contributors) == []
        child1 = ProjectFactory(parent=project)
        child2 = ProjectFactory(parent=child1)
        assert list(child1.admin_contributors) == [project.creator]
        assert (
            list(child2.admin_contributors) ==
            sorted([project.creator, child1.creator], key=lambda user: user.family_name)
        )
        admin = UserFactory()
        project.add_contributor(admin, auth=Auth(project.creator), permissions=['read', 'write', 'admin'])
        project.set_permissions(project.creator, ['read', 'write'])
        project.save()
        assert list(child1.admin_contributors) == [admin]
        assert list(child2.admin_contributors) == sorted([child1.creator, admin], key=lambda user: user.family_name)

    def test_admin_contributor_ids(self, user):
        project = ProjectFactory(creator=user)
        assert project.admin_contributor_ids == set()
        child1 = ProjectFactory(parent=project)
        child2 = ProjectFactory(parent=child1)
        assert child1.admin_contributor_ids == {project.creator._id}
        assert child2.admin_contributor_ids == {project.creator._id, child1.creator._id}
        admin = UserFactory()
        project.add_contributor(admin, auth=Auth(project.creator), permissions=['read', 'write', 'admin'])
        project.set_permissions(project.creator, ['read', 'write'])
        project.save()
        assert child1.admin_contributor_ids == {admin._id}
        assert child2.admin_contributor_ids == {child1.creator._id, admin._id}


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

    def test_is_admin_parent_target_admin(self, project):
        assert project.is_admin_parent(project.creator)

    def test_is_admin_parent_parent_admin(self, project):
        user = UserFactory()
        node = NodeFactory(parent=project, creator=user)
        assert node.is_admin_parent(project.creator)

    def test_is_admin_parent_grandparent_admin(self, project):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=project,
            category='project',
            creator=user
        )
        child_node = NodeFactory(parent=parent_node, creator=user)
        assert child_node.is_admin_parent(project.creator)
        assert parent_node.is_admin_parent(project.creator)

    def test_is_admin_parent_parent_write(self, project):
        user = UserFactory()
        node = NodeFactory(parent=project, creator=user)
        contrib = UserFactory()
        project.add_contributor(contrib, auth=Auth(project.creator), permissions=[READ, WRITE])
        assert node.is_admin_parent(contrib) is False

    def test_has_permission_read_parent_admin(self, project):
        user = UserFactory()
        node = NodeFactory(parent=project, creator=user)
        assert node.has_permission(project.creator, READ)
        assert node.has_permission(project.creator, ADMIN) is False

    def test_has_permission_read_grandparent_admin(self, project):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=project,
            category='project',
            creator=user
        )
        child_node = NodeFactory(
            parent=parent_node,
            creator=user
        )
        assert child_node.has_permission(project.creator, READ)
        assert child_node.has_permission(project.creator, ADMIN) is False
        assert parent_node.has_permission(project.creator, READ)
        assert parent_node.has_permission(project.creator, ADMIN) is False

    def test_can_view_parent_admin(self, project):
        user = UserFactory()
        node = NodeFactory(parent=project, creator=user)
        assert node.can_view(Auth(user=project.creator))
        assert node.can_edit(Auth(user=project.creator)) is False

    def test_can_view_grandparent_admin(self, project):
        user = UserFactory()
        parent_node = NodeFactory(
            parent=project,
            creator=user,
            category='project'
        )
        child_node = NodeFactory(
            parent=parent_node,
            creator=user
        )
        assert parent_node.can_view(Auth(user=project.creator))
        assert parent_node.can_edit(Auth(user=project.creator)) is False
        assert child_node.can_view(Auth(user=project.creator)) is True
        assert child_node.can_edit(Auth(user=project.creator)) is False

    def test_can_view_parent_write(self, project):
        user = UserFactory()
        node = NodeFactory(parent=project, creator=user)
        contrib = UserFactory()
        project.add_contributor(contrib, auth=Auth(project.creator), permissions=['read', 'write'])
        assert node.can_view(Auth(user=contrib)) is False
        assert node.can_edit(Auth(user=contrib)) is False

    def test_creator_cannot_edit_project_if_they_are_removed(self):
        creator = UserFactory()
        project = ProjectFactory(creator=creator)
        contrib = UserFactory()
        project.add_contributor(contrib, permissions=['read', 'write', 'admin'], auth=Auth(user=creator))
        project.save()
        assert creator in project.contributors.all()
        # Creator is removed from project
        project.remove_contributor(creator, auth=Auth(user=contrib))
        assert project.can_view(Auth(user=creator)) is False
        assert project.can_edit(Auth(user=creator)) is False
        assert project.is_contributor(creator) is False
    #
    # def test_can_view_public(self):
    #     # Create contributor and noncontributor
    #     contributor = UserFactory()
    #     contributor_auth = Auth(user=contributor)
    #     other_guy = UserFactory()
    #     other_guy_auth = Auth(user=other_guy)
    #     self.project.add_contributor(
    #         contributor=contributor, auth=self.auth)
    #     # Change project to public
    #     self.project.set_privacy('public')
    #     self.project.save()
    #     # Creator, contributor, and noncontributor can view
    #     assert self.project.can_view(self.auth)
    #     assert self.project.can_view(contributor_auth)
    #     assert self.project.can_view(other_guy_auth)
    #
    # def test_is_fork_of(self):
    #     project = ProjectFactory()
    #     fork1 = project.fork_node(auth=Auth(user=project.creator))
    #     fork2 = fork1.fork_node(auth=Auth(user=project.creator))
    #     assert_true(fork1.is_fork_of(project))
    #     assert_true(fork2.is_fork_of(project))
    #
    # def test_is_fork_of_false(self):
    #     project = ProjectFactory()
    #     to_fork = ProjectFactory()
    #     fork = to_fork.fork_node(auth=Auth(user=to_fork.creator))
    #     assert_false(fork.is_fork_of(project))
    #
    # def test_is_fork_of_no_forked_from(self):
    #     project = ProjectFactory()
    #     assert_false(project.is_fork_of(self.project))
    #
    # def test_is_registration_of(self):
    #     project = ProjectFactory()
    #     with mock_archive(project) as reg1:
    #         with mock_archive(reg1) as reg2:
    #             assert_true(reg1.is_registration_of(project))
    #             assert_true(reg2.is_registration_of(project))
    #
    # def test_is_registration_of_false(self):
    #     project = ProjectFactory()
    #     to_reg = ProjectFactory()
    #     with mock_archive(to_reg) as reg:
    #         assert_false(reg.is_registration_of(project))
    #
    # def test_raises_permissions_error_if_not_a_contributor(self):
    #     project = ProjectFactory()
    #     user = UserFactory()
    #     with assert_raises(PermissionsError):
    #         project.register_node(None, Auth(user=user), '', None)
    #
    # def test_admin_can_register_private_children(self):
    #     user = UserFactory()
    #     project = ProjectFactory(creator=user)
    #     project.set_permissions(user, ['admin', 'write', 'read'])
    #     child = NodeFactory(parent=project, is_public=False)
    #     assert_false(child.can_edit(auth=Auth(user=user)))  # sanity check
    #     with mock_archive(project, None, Auth(user=user), '', None) as registration:
    #         # child was registered
    #         child_registration = registration.nodes[0]
    #         assert_equal(child_registration.registered_from, child)
    #
    # def test_is_registration_of_no_registered_from(self):
    #     project = ProjectFactory()
    #     assert_false(project.is_registration_of(self.project))
    #
    # def test_registration_preserves_license(self):
    #     license = NodeLicenseRecordFactory()
    #     self.project.node_license = license
    #     self.project.save()
    #     with mock_archive(self.project, autocomplete=True) as registration:
    #         assert_equal(registration.node_license.id, license.id)
    #
    # def test_is_contributor_unregistered(self):
    #     unreg = UnregUserFactory()
    #     self.project.add_unregistered_contributor(
    #         fullname=fake.name(),
    #         email=unreg.username,
    #         auth=self.auth
    #     )
    #     self.project.save()
    #     assert_true(self.project.is_contributor(unreg))

class TestRegisterNode:

    def test_register_node_creates_new_registration(self, node, auth):
        with disconnected_from_listeners(after_create_registration):
            registration = node.register_node(get_default_metaschema(), auth, '', None)
            assert type(registration) is Registration
            assert node._id != registration._id

# Copied from tests/test_models.py
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


def test_find_by_institutions():
    inst1, inst2 = InstitutionFactory(), InstitutionFactory()
    project = ProjectFactory(is_public=True)
    user = project.creator
    user.affiliated_institutions.add(inst1, inst2)
    project.add_affiliated_institution(inst1, user=user)
    project.save()

    inst1_result = Node.find_by_institutions(inst1)
    assert project in inst1_result.all()

    inst2_result = Node.find_by_institutions(inst2)
    assert project not in inst2_result.all()


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


def test_parent_kwarg():
    parent = NodeFactory()
    child = NodeFactory(parent=parent)
    assert child.parent_node == parent
    assert child in parent._nodes.all()


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

    @mock.patch('osf.models.queued_mail.queue_mail')
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
        with mock.patch('osf.models.Registration.request_embargo_termination') as mock_request_embargo_termination:
            registration.set_privacy('public', auth=auth)
            assert mock_request_embargo_termination.call_count == 1

# copied from tests/test_models.py
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

    def test_manage_contributors_reordering(self, node, user, auth):
        user2, user3 = UserFactory(), UserFactory()
        node.add_contributor(contributor=user2, auth=auth)
        node.add_contributor(contributor=user3, auth=auth)
        node.save()
        assert list(node.contributors.all()) == [user, user2, user3]
        node.manage_contributors(
            user_dicts=[
                {
                    'id': user2._id,
                    'permission': WRITE,
                    'visible': True,
                },
                {
                    'id': user3._id,
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
        assert list(node.contributors.all()) == [user2, user3, user]

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

    def test_manage_contributors_logs_when_permissions_change(self, node, user, auth):
        user2 = UserFactory()
        node.add_contributor(contributor=user2, permissions=[READ, WRITE], auth=auth)
        node.save()
        node.manage_contributors(
            user_dicts=[
                {
                    'id': user._id,
                    'permission': ADMIN,
                    'visible': True,
                },
                {
                    'id': user2._id,
                    'permission': READ,
                    'visible': True,
                },
            ],
            auth=auth,
            save=True
        )
        latest_log = node.logs.latest()
        assert latest_log.action == NodeLog.PERMISSIONS_UPDATED
        assert latest_log.user == user
        assert user2._id in latest_log.params['contributors']
        assert user._id not in latest_log.params['contributors']

    def test_manage_contributors_new_contributor(self, node, user, auth):
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

    @mock.patch('osf.models.node.AbstractNode.update_search')
    def test_delete_registration_tree(self, mock_update_search):
        proj = NodeFactory()
        NodeFactory(parent=proj)
        comp2 = NodeFactory(parent=proj)
        NodeFactory(parent=comp2)
        reg = RegistrationFactory(project=proj)
        reg_ids = [reg._id] + [r._id for r in reg.get_descendants_recursive()]
        orig_call_count = mock_update_search.call_count
        reg.delete_registration_tree(save=True)
        assert Node.find(Q('_id', 'in', reg_ids) & Q('is_deleted', 'eq', False)).count() == 0
        assert mock_update_search.call_count == orig_call_count + len(reg_ids)

    def test_delete_registration_tree_sets_draft_registration_approvals_to_none(self, user):
        ensure_schemas()
        reg = RegistrationFactory()

        dr = DraftRegistrationFactory(initiator=user)
        approval = DraftRegistrationApproval(state=Sanction.APPROVED)
        approval.save()
        dr.approval = approval
        dr.registered_node = reg
        dr.save()

        reg.delete_registration_tree(save=True)

        dr.reload()
        assert dr.approval is None

    @mock.patch('osf.models.node.AbstractNode.update_search')
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

    def test_get_descendants_recursive_cyclic(self, user, root, auth):
        point1 = ProjectFactory(creator=user, parent=root)
        point2 = ProjectFactory(creator=user, parent=root)
        point1.add_pointer(point2, auth=auth)
        point2.add_pointer(point1, auth=auth)

        descendants = list(point1.get_descendants_recursive())
        assert len(descendants) == 1

def test_linked_from(node, auth):
    registration_to_link = RegistrationFactory()
    node_to_link = NodeFactory()

    node.add_pointer(node_to_link, auth=auth)
    node.add_pointer(registration_to_link, auth=auth)
    node.save()

    assert node in node_to_link.linked_from.all()
    assert node in registration_to_link.linked_from.all()


# Copied from tests/test_models.py
class TestPointerMethods:

    def test_add_pointer(self, node, user, auth):
        node2 = NodeFactory(creator=user)
        node.add_pointer(node2, auth=auth)
        assert node2 in node.linked_nodes.all()
        assert (
            node.logs.latest().action == NodeLog.POINTER_CREATED
        )
        assert (
            node.logs.latest().params == {
                'parent_node': node.parent_id,
                'node': node._primary_key,
                'pointer': {
                    'id': node2._id,
                    'url': node2.url,
                    'title': node2.title,
                    'category': node2.category,
                },
            }
        )

    def test_add_linked_nodes_property(self, node, auth):
        child = NodeFactory(parent=node)
        node_link = ProjectFactory()
        node.add_pointer(node_link, auth=auth, save=True)

        assert node_link in node.linked_nodes.all()
        assert child not in node.linked_nodes.all()

    def test_nodes_primary_does_not_return_linked_nodes(self, node, auth):
        child = NodeFactory(parent=node)
        node_link = ProjectFactory()
        node.add_pointer(node_link, auth=auth, save=True)

        assert child in node.nodes_primary.all()
        assert node_link not in node.nodes_primary.all()

    def test_add_pointer_adds_to_end_of_nodes(self, node, user, auth):
        child = NodeFactory(parent=node)
        child2 = NodeFactory(parent=node)

        node_link = ProjectFactory()

        node.add_pointer(node_link, auth=auth, save=True)

        nodes = list(node.nodes)
        assert child == nodes[0]
        assert child2 == nodes[1]
        assert node_link == nodes[2]

    def test_add_pointer_fails_for_registrations(self, user, auth):
        node = ProjectFactory()
        registration = RegistrationFactory(creator=user)

        with pytest.raises(NodeStateError):
            registration.add_pointer(node, auth=auth)

    def test_get_points_exclude_folders(self):
        user = UserFactory()
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in a organizer collection
        folder = CollectionFactory(creator=pointed_project.creator)
        folder.add_pointer(pointed_project, Auth(pointed_project.creator), save=True)

        assert pointer_project in pointed_project.get_points(folders=False)
        assert folder not in pointed_project.get_points(folders=False)
        assert folder in pointed_project.get_points(folders=True)

    def test_get_points_exclude_deleted(self):
        user = UserFactory()
        pointer_project = ProjectFactory(is_public=True, is_deleted=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        assert pointer_project not in pointed_project.get_points(deleted=False)
        assert pointer_project in pointed_project.get_points(deleted=True)

    def test_add_pointer_already_present(self, node, user, auth):
        node2 = NodeFactory(creator=user)
        node.add_pointer(node2, auth=auth)
        with pytest.raises(ValueError):
            node.add_pointer(node2, auth=auth)

    def test_rm_pointer(self, node, user, auth):
        node2 = NodeFactory(creator=user)
        node_relation = node.add_pointer(node2, auth=auth)
        node.rm_pointer(node_relation, auth=auth)
        # assert Pointer.load(pointer._id) is None
        # assert len(node.nodes) == 0
        assert len(node2.get_points()) == 0
        assert (
            node.logs.latest().action == NodeLog.POINTER_REMOVED
        )
        assert(
            node.logs.latest().params == {
                'parent_node': node.parent_id,
                'node': node._primary_key,
                'pointer': {
                    'id': node2._id,
                    'url': node2.url,
                    'title': node2.title,
                    'category': node2.category,
                },
            }
        )

    def test_rm_pointer_not_present(self, user, node, auth):
        node_relation = NodeRelationFactory()
        with pytest.raises(ValueError):
            node.rm_pointer(node_relation, auth=auth)

    def test_fork_pointer_not_present(self, node, auth):
        node_relation = NodeRelationFactory()
        with pytest.raises(ValueError):
            node.fork_pointer(node_relation, auth=auth)

    def _fork_pointer(self, node, content, auth):
        pointer = node.add_pointer(content, auth=auth)
        forked = node.fork_pointer(pointer, auth=auth)
        assert forked.is_fork is True
        assert forked.forked_from == content
        assert forked.primary is True
        assert node._nodes.first() == forked
        assert(
            node.logs.latest().action == NodeLog.POINTER_FORKED
        )
        assert content not in node._nodes.all()
        assert(
            node.logs.latest().params == {
                'parent_node': node.parent_id,
                'node': node._primary_key,
                'pointer': {
                    'id': content._id,
                    'url': content.url,
                    'title': content.title,
                    'category': content.category,
                },
            }
        )

    def test_fork_pointer_project(self, node, user, auth):
        project = ProjectFactory(creator=user)
        self._fork_pointer(node=node, content=project, auth=auth)

    def test_fork_pointer_component(self, node, user, auth):
        component = NodeFactory(creator=user)
        self._fork_pointer(node=node, content=component, auth=auth)

# copied from tests/test_models.py
class TestForkNode:

    def _cmp_fork_original(self, fork_user, fork_date, fork, original,
                           title_prepend='Fork of '):
        """Compare forked node with original node. Verify copied fields,
        modified fields, and files; recursively compare child nodes.

        :param fork_user: User who forked the original nodes
        :param fork_date: Datetime (UTC) at which the original node was forked
        :param fork: Forked node
        :param original: Original node
        :param title_prepend: String prepended to fork title

        """
        # Test copied fields
        assert title_prepend + original.title == fork.title
        assert original.category == fork.category
        assert original.description == fork.description
        assert fork.logs.count() == original.logs.count() + 1
        assert original.logs.latest().action != NodeLog.NODE_FORKED
        assert fork.logs.latest().action == NodeLog.NODE_FORKED
        assert list(original.tags.values_list('name', flat=True)) == list(fork.tags.values_list('name', flat=True))
        assert (original.parent_node is None) == (fork.parent_node is None)

        # Test modified fields
        assert fork.is_fork is True
        assert fork.private_links.count() == 0
        assert fork.forked_from == original
        assert fork._id in [n._id for n in original.forks.all()]
        # Note: Must cast ForeignList to list for comparison
        assert list(fork.contributors.all()) == [fork_user]
        assert (fork_date - fork.date_created) < datetime.timedelta(seconds=30)
        assert fork.forked_date != original.date_created

        # Test that pointers were copied correctly
        assert(
            list(original.nodes_pointer.all()) == list(fork.nodes_pointer.all())
        )

        # Test that add-ons were copied correctly
        assert(
            original.get_addon_names() ==
            fork.get_addon_names()
        )
        assert(
            [addon.config.short_name for addon in original.get_addons()] ==
            [addon.config.short_name for addon in fork.get_addons()]
        )

        fork_user_auth = Auth(user=fork_user)
        # Recursively compare children
        for idx, child in enumerate(original.get_nodes()):
            if child.can_view(fork_user_auth):
                self._cmp_fork_original(fork_user, fork_date, fork.get_nodes()[idx],
                                        child, title_prepend='')

    @mock.patch('framework.status.push_status_message')
    def test_fork_recursion(self, mock_push_status_message, node, user, auth, request_context):
        """Omnibus test for forking.
        """
        # Make some children
        component = NodeFactory(creator=user, parent=node)
        subproject = ProjectFactory(creator=user, parent=node)

        # Add pointers to test copying
        pointee = ProjectFactory()
        node.add_pointer(pointee, auth=auth)
        component.add_pointer(pointee, auth=auth)
        subproject.add_pointer(pointee, auth=auth)

        # Add add-on to test copying
        node.add_addon('dropbox', auth)
        component.add_addon('dropbox', auth)
        subproject.add_addon('dropbox', auth)

        # Log time
        fork_date = timezone.now()

        # Fork node
        with mock.patch.object(Node, 'bulk_update_search'):
            fork = node.fork_node(auth=auth)

        # Compare fork to original
        self._cmp_fork_original(user, fork_date, fork, node)

    def test_forked_component_has_parent_node(self, node, auth):
        assert node.parent_node

        fork = node.fork_node(auth=auth)
        assert fork.parent_node == node.parent_node

    def test_fork_private_children(self, node, user, auth):
        """Tests that only public components are created

        """
        # Make project public
        node.set_privacy('public')
        # Make some children
        # public component
        NodeFactory(
            creator=user,
            parent=node,
            title='Forked',
            is_public=True,
        )
        # public subproject
        ProjectFactory(
            creator=user,
            parent=node,
            title='Forked',
            is_public=True,
        )
        # private component
        NodeFactory(
            creator=user,
            parent=node,
            title='Not Forked',
        )
        # private subproject
        private_subproject = ProjectFactory(
            creator=user,
            parent=node,
            title='Not Forked',
        )
        # private subproject public component
        NodeFactory(
            creator=user,
            parent=private_subproject,
            title='Not Forked',
        )
        # public subproject public component
        NodeFactory(
            creator=user,
            parent=private_subproject,
            title='Forked',
        )
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = None
        # New user forks the project
        fork = node.fork_node(user2_auth)

        # fork correct children
        assert fork._nodes.count() == 2
        assert 'Not Forked' not in fork._nodes.values_list('title', flat=True)

    def test_fork_not_public(self, node, auth):
        node.set_privacy('public')
        fork = node.fork_node(auth)
        assert fork.is_public is False

    def test_fork_log_has_correct_log(self, node, auth):
        fork = node.fork_node(auth)
        last_log = fork.logs.latest()
        assert last_log.action == NodeLog.NODE_FORKED
        # Legacy 'registration' param should be the ID of the fork
        assert last_log.params['registration'] == fork._primary_key
        # 'node' param is the original node's ID
        assert last_log.params['node'] == node._id

    def test_not_fork_private_link(self, node, auth):
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        fork = node.fork_node(auth)
        assert link not in fork.private_links.all()

    def test_cannot_fork_private_node(self, node):
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        with pytest.raises(PermissionsError):
            node.fork_node(user2_auth)

    def test_can_fork_public_node(self, node):
        node.set_privacy('public')
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = node.fork_node(user2_auth)
        assert bool(fork) is True

    def test_contributor_can_fork(self, node):
        user2 = UserFactory()
        node.add_contributor(user2)
        user2_auth = Auth(user=user2)
        fork = node.fork_node(user2_auth)
        assert bool(fork) is True
        # Forker has admin permissions
        assert fork.contributors.count() == 1
        assert fork.get_permissions(user2) == ['read', 'write', 'admin']

    def test_fork_preserves_license(self, node, auth):
        license = NodeLicenseRecordFactory()
        node.node_license = license
        node.save()
        fork = node.fork_node(auth)
        assert fork.node_license.license_id == license.license_id

    def test_fork_registration(self, user, node, auth):
        registration = RegistrationFactory(project=node)
        fork = registration.fork_node(auth)

        # fork should not be a registration
        assert fork.is_registration is False

        # Compare fork to original
        self._cmp_fork_original(
            user,
            timezone.now(),
            fork,
            registration,
        )

    def test_fork_project_with_no_wiki_pages(self, user, auth):
        project = ProjectFactory(creator=user)
        fork = project.fork_node(auth)
        assert fork.wiki_pages_versions == {}
        assert fork.wiki_pages_current == {}
        assert fork.wiki_private_uuids == {}

    def test_forking_clones_project_wiki_pages(self, user, auth):
        project = ProjectFactory(creator=user, is_public=True)
        # TODO: Unmock when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki = NodeWikiFactory(node=project)
            current_wiki = NodeWikiFactory(node=project, version=2)
        fork = project.fork_node(auth)
        assert fork.wiki_private_uuids == {}

        registration_wiki_current = NodeWikiPage.load(fork.wiki_pages_current[current_wiki.page_name])
        assert registration_wiki_current.node == fork
        assert registration_wiki_current._id != current_wiki._id

        registration_wiki_version = NodeWikiPage.load(fork.wiki_pages_versions[wiki.page_name][0])
        assert registration_wiki_version.node == fork
        assert registration_wiki_version._id != wiki._id

class TestAlternativeCitationMethods:

    def test_add_citation(self, node, auth, fake):
        name, text = fake.bs(), fake.sentence()
        node.add_citation(auth=auth, save=True, name=name, text=text)
        assert node.alternative_citations.count() == 1

        latest_log = node.logs.latest()
        assert latest_log.action == NodeLog.CITATION_ADDED
        assert latest_log.params['node'] == node._id
        assert latest_log.params['citation'] == {
            'name': name, 'text': text
        }


class TestContributorOrdering:

    def test_can_get_contributor_order(self, node):
        user1, user2 = UserFactory(), UserFactory()
        contrib1 = Contributor.objects.create(user=user1, node=node)
        contrib2 = Contributor.objects.create(user=user2, node=node)
        creator_contrib = Contributor.objects.get(user=node.creator, node=node)
        assert list(node.get_contributor_order()) == [creator_contrib.id, contrib1.id, contrib2.id]
        assert list(node.contributors.all()) == [node.creator, user1, user2]

    def test_can_set_contributor_order(self, node):
        user1, user2 = UserFactory(), UserFactory()
        contrib1 = Contributor.objects.create(user=user1, node=node)
        contrib2 = Contributor.objects.create(user=user2, node=node)
        creator_contrib = Contributor.objects.get(user=node.creator, node=node)
        node.set_contributor_order([contrib1.id, contrib2.id, creator_contrib.id])
        assert list(node.get_contributor_order()) == [contrib1.id, contrib2.id, creator_contrib.id]
        assert list(node.contributors.all()) == [user1, user2, node.creator]

    def test_move_contributor(self, user, node, auth):
        user1 = UserFactory()
        user2 = UserFactory()
        node.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': True}
            ],
            auth=auth
        )

        user_contrib_id = node.contributor_set.get(user=user).id
        user1_contrib_id = node.contributor_set.get(user=user1).id
        user2_contrib_id = node.contributor_set.get(user=user2).id

        old_order = [user_contrib_id, user1_contrib_id, user2_contrib_id]
        assert list(node.get_contributor_order()) == old_order

        node.move_contributor(user=user2, auth=auth, index=0, save=True)

        new_order = [user2_contrib_id, user_contrib_id, user1_contrib_id]
        assert list(node.get_contributor_order()) == new_order


class TestNodeOrdering:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def children(self, project):
        child1 = NodeFactory(parent=project, is_public=False)
        child2 = NodeFactory(parent=project, is_public=False)
        child3 = NodeFactory(parent=project, is_public=True)

        rel1 = NodeRelation.objects.get(parent=project, child=child1)
        rel2 = NodeRelation.objects.get(parent=project, child=child2)
        rel3 = NodeRelation.objects.get(parent=project, child=child3)
        project.set_noderelation_order([rel2.pk, rel3.pk, rel1.pk])

        return [child1, child2, child3]

    def test_can_get_node_relation_order(self, project, children):
        assert list(project.get_noderelation_order()) == [e.pk for e in project.node_relations.all()]

    def test_nodes_property_returns_ordered_nodes(self, project, children):
        nodes = list(project.nodes)
        assert len(nodes) == 3
        assert nodes == [children[1], children[2], children[0]]

    def test_get_nodes_no_filter(self, project, children):
        nodes = list(project.get_nodes())
        assert nodes == [children[1], children[2], children[0]]

    def test_get_nodes_with_filter(self, project, children):
        public_nodes = list(project.get_nodes(is_public=True))
        assert public_nodes == [children[2]]

        private_nodes = list(project.get_nodes(is_public=False))
        assert private_nodes == [children[1], children[0]]

    def test_get_nodes_does_not_return_duplicates(self):
        parent = ProjectFactory(title='Parent')
        child = NodeFactory(parent=parent, title='Child', is_public=True)
        linker = ProjectFactory(title='Linker', is_public=True)
        unrelated = ProjectFactory(title='Unrelated', is_public=True)

        linker.add_node_link(child, auth=Auth(linker.creator), save=True)
        linker.add_node_link(unrelated, auth=Auth(linker.creator), save=True)

        rel1 = NodeRelation.objects.get(parent=linker, child=child)
        rel2 = NodeRelation.objects.get(parent=linker, child=unrelated)
        linker.set_noderelation_order([rel2.pk, rel1.pk])

        assert len(parent.get_nodes()) == 1  # child
        assert len(linker.get_nodes()) == 2  # child and unrelated

def test_node_ids(node):
    child1, child2 = NodeFactory(parent=node), NodeFactory(parent=node)

    assert child1._id in node.node_ids
    assert child2._id in node.node_ids


def test_templated_list(node):
    templated1, templated2 = ProjectFactory(template_node=node), NodeFactory(template_node=node)
    deleted = ProjectFactory(template_node=node, is_deleted=True)

    assert node.templated_list.count() == 2
    assert templated1 in node.templated_list.all()
    assert templated2 in node.templated_list.all()
    assert deleted not in node.templated_list.all()


def test_querying_on_contributors(node, user, auth):
    deleted = NodeFactory(is_deleted=True)
    deleted.add_contributor(user, auth=auth)
    deleted.save()
    result = list(Node.find(Q('contributors', 'eq', user)).all())
    assert node in result
    assert deleted in result

    result2 = list(Node.find(Q('contributors', 'eq', user) & Q('is_deleted', 'eq', False)).all())
    assert node in result2
    assert deleted not in result2


class TestLogMethods:

    @pytest.fixture()
    def parent(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def node(self, parent):
        return NodeFactory(parent=parent)

    def test_get_aggregate_logs_queryset_recurses(self, parent, node, auth):
        grandchild = NodeFactory(parent=node)
        parent_log = parent.add_log(NodeLog.FILE_ADDED, auth=auth, params={'node': parent._id}, save=True)
        child_log = node.add_log(NodeLog.FILE_ADDED, auth=auth, params={'node': node._id}, save=True)
        grandchild_log = grandchild.add_log(NodeLog.FILE_ADDED, auth=auth, params={'node': grandchild._id}, save=True)
        logs = parent.get_aggregate_logs_queryset(auth)
        assert parent_log in list(logs)
        assert child_log in list(logs)
        assert grandchild_log in list(logs)

    # copied from tests/test_models.py#TestNode
    def test_get_aggregate_logs_queryset_doesnt_return_hidden_logs(self, parent):
        n_orig_logs = len(parent.get_aggregate_logs_queryset(Auth(user)))

        log = parent.logs.latest()
        log.should_hide = True
        log.save()

        n_new_logs = len(parent.get_aggregate_logs_queryset(Auth(user)))
        # Hidden log is not returned
        assert n_new_logs == n_orig_logs - 1

# copied from tests/test_notifications.py
class TestHasPermissionOnChildren:

    def test_has_permission_on_children(self):
        non_admin_user = UserFactory()
        parent = ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = NodeFactory(parent=parent, category='project')
        sub_component = NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.save()
        NodeFactory(parent=node)  # another subcomponent

        assert(
            node.has_permission_on_children(non_admin_user, 'read')
        ) is True

    def test_check_user_has_permission_excludes_deleted_components(self):
        non_admin_user = UserFactory()
        parent = ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = NodeFactory(parent=parent, category='project')
        sub_component = NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.is_deleted = True
        sub_component.save()
        NodeFactory(parent=node)

        assert(
            node.has_permission_on_children(non_admin_user, 'read')
        ) is False

    def test_check_user_does_not_have_permission_on_private_node_child(self):
        non_admin_user = UserFactory()
        parent = ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = NodeFactory(parent=parent, category='project')
        NodeFactory(parent=node)

        assert (
            node.has_permission_on_children(non_admin_user, 'read')
        ) is False

    def test_check_user_child_node_permissions_false_if_no_children(self):
        non_admin_user = UserFactory()
        parent = ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = NodeFactory(parent=parent, category='project')

        assert(
            node.has_permission_on_children(non_admin_user, 'read')
        ) is False

    def test_check_admin_has_permissions_on_private_component(self):
        parent = ProjectFactory()
        node = NodeFactory(parent=parent, category='project')
        NodeFactory(parent=node)

        assert (
            node.has_permission_on_children(parent.creator, 'read')
        ) is True

    def test_check_user_private_node_child_permissions_excludes_pointers(self):
        user = UserFactory()
        parent = ProjectFactory()
        pointed = ProjectFactory(creator=user)
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()

        assert (
            parent.has_permission_on_children(user, 'read')
        ) is False


# copied from test/test_citations.py#CitationsNodeTestCase
class TestCitationsProperties:

    def test_csl_single_author(self, node):
        # Nodes with one contributor generate valid CSL-data
        assert (
            node.csl ==
            {
                'publisher': 'Open Science Framework',
                'author': [{
                    'given': node.creator.given_name,
                    'family': node.creator.family_name,
                }],
                'URL': node.display_absolute_url,
                'issued': datetime_to_csl(node.logs.latest().date),
                'title': node.title,
                'type': 'webpage',
                'id': node._id,
            }
        )

    def test_csl_multiple_authors(self, node):
        # Nodes with multiple contributors generate valid CSL-data
        user = UserFactory()
        node.add_contributor(user)
        node.save()

        assert (
            node.csl ==
            {
                'publisher': 'Open Science Framework',
                'author': [
                    {
                        'given': node.creator.given_name,
                        'family': node.creator.family_name,
                    },
                    {
                        'given': user.given_name,
                        'family': user.family_name,
                    }
                ],
                'URL': node.display_absolute_url,
                'issued': datetime_to_csl(node.logs.latest().date),
                'title': node.title,
                'type': 'webpage',
                'id': node._id,
            }
        )

    def test_non_visible_contributors_arent_included_in_csl(self):
        node = ProjectFactory()
        visible = UserFactory()
        node.add_contributor(visible, auth=Auth(node.creator))
        invisible = UserFactory()
        node.add_contributor(invisible, auth=Auth(node.creator), visible=False)
        node.save()
        assert len(node.csl['author']) == 2
        expected_authors = [
            contrib.csl_name for contrib in [node.creator, visible]
        ]

        assert node.csl['author'] == expected_authors


# copied from tests/test_models.py
class TestNodeUpdate:

    def test_update_title(self, fake, auth, node):
        # Creator (admin) can update
        new_title = fake.catch_phrase()
        node.update({'title': new_title}, auth=auth, save=True)
        assert node.title == new_title

        last_log = node.logs.latest()
        assert last_log.action == NodeLog.EDITED_TITLE

        # Write contrib can update
        new_title2 = fake.catch_phrase()
        write_contrib = UserFactory()
        node.add_contributor(write_contrib, auth=auth, permissions=(READ, WRITE))
        node.save()
        node.update({'title': new_title2}, auth=auth)
        assert node.title == new_title2

    def test_update_description(self, fake, node, auth):
        new_title = fake.bs()

        node.update({'title': new_title}, auth=auth)
        assert node.title == new_title

        last_log = node.logs.latest()
        assert last_log.action == NodeLog.EDITED_TITLE

    def test_update_title_and_category(self, fake, node, auth):
        new_title = fake.bs()

        new_category = 'data'

        node.update({'title': new_title, 'category': new_category}, auth=auth, save=True)
        assert node.title == new_title
        assert node.category == 'data'

        logs = node.logs.order_by('-date')
        last_log, penultimate_log = logs[:2]
        assert penultimate_log.action == NodeLog.EDITED_TITLE
        assert last_log.action == NodeLog.UPDATED_FIELDS

    def test_update_is_public(self, node, user, auth):
        node.update({'is_public': True}, auth=auth, save=True)
        assert node.is_public

        last_log = node.logs.latest()
        assert last_log.action == NodeLog.MADE_PUBLIC

        node.update({'is_public': False}, auth=auth, save=True)
        last_log = node.logs.latest()
        assert last_log.action == NodeLog.MADE_PRIVATE

    def test_update_can_make_registration_public(self):
        reg = RegistrationFactory(is_public=False)
        reg.update({'is_public': True})

        assert reg.is_public
        last_log = reg.logs.latest()
        assert last_log.action == NodeLog.MADE_PUBLIC

    def test_updating_title_twice_with_same_title(self, fake, auth, node):
        original_n_logs = node.logs.count()
        new_title = fake.bs()
        node.update({'title': new_title}, auth=auth, save=True)
        assert node.logs.count() == original_n_logs + 1  # sanity check

        # Call update with same title
        node.update({'title': new_title}, auth=auth, save=True)
        # A new log is not created
        assert node.logs.count() == original_n_logs + 1

    def test_updating_description_twice_with_same_content(self, fake, auth, node):
        original_n_logs = node.logs.count()
        new_desc = fake.bs()
        node.update({'description': new_desc}, auth=auth, save=True)
        assert node.logs.count() == original_n_logs + 1  # sanity check

        # Call update with same description
        node.update({'description': new_desc}, auth=auth, save=True)
        # A new log is not created
        assert node.logs.count() == original_n_logs + 1

    # Regression test for https://openscience.atlassian.net/browse/OSF-4664
    def test_updating_category_twice_with_same_content_generates_one_log(self, node, auth):
        node.category = 'project'
        node.save()
        original_n_logs = node.logs.count()
        new_category = 'data'

        node.update({'category': new_category}, auth=auth, save=True)
        assert node.logs.count() == original_n_logs + 1  # sanity check
        assert node.category == new_category

        # Call update with same category
        node.update({'category': new_category}, auth=auth, save=True)

        # Only one new log is created
        assert node.logs.count() == original_n_logs + 1
        assert node.category == new_category

    # TODO: test permissions, non-writable fields

# copied from tests/test_models.py
class TestRemoveNode:

    @pytest.fixture()
    def parent_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def project(self, parent_project, user):
        return ProjectFactory(creator=user, parent=parent_project)

    def test_remove_project_without_children(self, parent_project, project, auth):
        project.remove_node(auth=auth)

        assert project.is_deleted
        # parent node should have a log of the event
        assert (
            parent_project.get_aggregate_logs_queryset(auth)[0].action ==
            'node_removed'
        )

    def test_delete_project_log_present(self, project, parent_project, auth):
        project.remove_node(auth=auth)
        parent_project.remove_node(auth=auth)

        assert parent_project.is_deleted
        # parent node should have a log of the event
        assert parent_project.logs.latest().action == 'project_deleted'

    def test_remove_project_with_project_child_fails(self, parent_project, project, auth):
        with pytest.raises(NodeStateError):
            parent_project.remove_node(auth)

    def test_remove_project_with_component_child_fails(self, user, project, parent_project, auth):
        NodeFactory(creator=user, parent=project)

        with pytest.raises(NodeStateError):
            parent_project.remove_node(auth)

    def test_remove_project_with_pointer_child(self, auth, user, project, parent_project):
        target = ProjectFactory(creator=user)
        project.add_pointer(node=target, auth=auth)

        assert project.linked_nodes.count() == 1

        project.remove_node(auth=auth)

        assert (project.is_deleted)
        # parent node should have a log of the event
        assert parent_project.logs.latest().action == 'node_removed'

        # target node shouldn't be deleted
        assert target.is_deleted is False


class TestTemplateNode:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    def _verify_log(self, node):
        """Tests to see that the "created from" log event is present (alone).

        :param node: A node having been created from a template just prior
        """
        assert node.logs.count() == 1
        assert node.logs.latest().action == NodeLog.CREATED_FROM

    def test_simple_template(self, project, auth):
        """Create a templated node, with no changes"""
        # created templated node
        new = project.use_as_template(
            auth=auth
        )

        assert new.title == self._default_title(project)
        assert new.date_created != project.date_created
        self._verify_log(new)

    def test_simple_template_title_changed(self, project, auth):
        """Create a templated node, with the title changed"""
        changed_title = 'Made from template'

        # create templated node
        new = project.use_as_template(
            auth=auth,
            changes={
                project._primary_key: {
                    'title': changed_title,
                }
            }
        )

        assert new.title == changed_title
        assert new.date_created != project.date_created
        self._verify_log(new)

    def test_use_as_template_adds_default_addons(self, project, auth):
        new = project.use_as_template(
            auth=auth
        )

        assert new.has_addon('wiki')
        assert new.has_addon('osfstorage')

    def test_use_as_template_preserves_license(self, project, auth):
        license = NodeLicenseRecordFactory()
        project.node_license = license
        project.save()
        new = project.use_as_template(
            auth=auth
        )

        assert new.license.node_license._id == license.node_license._id
        self._verify_log(new)

    @pytest.fixture()
    def pointee(self, project, user, auth):
        pointee = ProjectFactory(creator=user)
        project.add_pointer(pointee, auth=auth)
        return pointee

    @pytest.fixture()
    def component(self, user, project):
        return NodeFactory(creator=user, parent=project)

    @pytest.fixture()
    def subproject(self, user, project):
        return ProjectFactory(creator=user, parent=project)

    @staticmethod
    def _default_title(x):
        if isinstance(x, Node):
            return str(language.TEMPLATED_FROM_PREFIX + x.title)
        return str(x.title)

    def test_complex_template(self, auth, project, pointee, component, subproject):
        """Create a templated node from a node with children"""

        # create templated node
        new = project.use_as_template(auth=auth)

        assert new.title == self._default_title(project)
        assert len(list(new.nodes)) == len(list(project.nodes))
        # check that all children were copied
        assert (
            [x.title for x in new.nodes] ==
            [x.title for x in project.nodes]
        )
        # ensure all child nodes were actually copied, instead of moved
        assert {x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in project.nodes}
        )

    def test_complex_template_titles_changed(self, auth, project, pointee, component, subproject):

        # build changes dict to change each node's title
        changes = {
            x._primary_key: {
                'title': 'New Title ' + str(idx)
            } for idx, x in enumerate(project.nodes)
        }

        # create templated node
        new = project.use_as_template(
            auth=auth,
            changes=changes
        )

        for old_node, new_node in zip(project.nodes, new.nodes):
            if isinstance(old_node, Node):
                assert (
                    changes[old_node._primary_key]['title'] ==
                    new_node.title
                )
            else:
                assert (
                    old_node.title ==
                    new_node.title
                )

    def test_template_wiki_pages_not_copied(self, project, auth):
        project.update_node_wiki(
            'template', 'lol',
            auth=auth
        )
        new = project.use_as_template(
            auth=auth
        )
        assert 'template' in project.wiki_pages_current
        assert 'template' in project.wiki_pages_versions
        assert new.wiki_pages_current == {}
        assert new.wiki_pages_versions == {}

    def test_user_who_makes_node_from_template_has_creator_permission(self):
        project = ProjectFactory(is_public=True)
        user = UserFactory()
        auth = Auth(user)

        templated = project.use_as_template(auth)

        assert templated.get_permissions(user) == ['read', 'write', 'admin']

    def test_template_security(self, user, auth, project, pointee, component, subproject):
        """Create a templated node from a node with public and private children

        Children for which the user has no access should not be copied
        """
        other_user = UserFactory()
        other_user_auth = Auth(user=other_user)

        # set two projects to public - leaving self.component as private
        project.is_public = True
        project.save()
        subproject.is_public = True
        subproject.save()

        # add new children, for which the user has each level of access
        read = NodeFactory(creator=user, parent=project)
        read.add_contributor(other_user, permissions=['read', ])
        read.save()

        write = NodeFactory(creator=user, parent=project)
        write.add_contributor(other_user, permissions=['read', 'write'])
        write.save()

        admin = NodeFactory(creator=user, parent=project)
        admin.add_contributor(other_user)
        admin.save()

        # filter down self.nodes to only include projects the user can see
        visible_nodes = filter(
            lambda x: x.can_view(other_user_auth),
            project.nodes
        )

        # create templated node
        new = project.use_as_template(auth=other_user_auth)

        assert new.title == self._default_title(project)

        # check that all children were copied
        assert (
            set(x.template_node._id for x in new.nodes) ==
            set(x._id for x in visible_nodes)
        )
        # ensure all child nodes were actually copied, instead of moved
        assert bool({x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in project.nodes}
        )) is True

        # ensure that the creator is admin for each node copied
        for node in new.nodes:
            assert (
                node.get_permissions(other_user) ==
                ['read', 'write', 'admin']
            )


# copied from tests/test_models.py
class TestAddonMethods:

    def test_add_addon(self, node, auth):
        addon_count = len(node.get_addon_names())
        addon_record_count = len(node.addons)
        added = node.add_addon('dropbox', auth)
        assert bool(added) is True
        node.reload()
        assert (
            len(node.get_addon_names()) ==
            addon_count + 1
        )
        assert (
            len(node.addons) ==
            addon_record_count + 1
        )
        assert (
            node.logs.latest().action ==
            NodeLog.ADDON_ADDED
        )

    def test_add_existing_addon(self, node, auth):
        addon_count = len(node.get_addon_names())
        addon_record_count = len(node.addons)
        added = node.add_addon('wiki', auth)
        assert bool(added) is False
        assert (
            len(node.get_addon_names()) ==
            addon_count
        )
        assert (
            len(node.addons) ==
            addon_record_count
        )

    def test_delete_addon(self, node, auth):
        addon_count = len(node.get_addon_names())
        deleted = node.delete_addon('wiki', auth)
        assert deleted is True
        assert (
            len(node.get_addon_names()) ==
            addon_count - 1
        )
        assert (
            node.logs.latest().action ==
            NodeLog.ADDON_REMOVED
        )

    @mock.patch('addons.dropbox.models.NodeSettings.config')
    def test_delete_mandatory_addon(self, mock_config, node, auth):
        mock_config.added_mandatory = ['node']
        node.add_addon('dropbox', auth)
        with pytest.raises(ValueError):
            node.delete_addon('dropbox', auth)

    def test_delete_nonexistent_addon(self, node, auth):
        addon_count = len(node.get_addon_names())
        deleted = node.delete_addon('dropbox', auth)
        assert bool(deleted) is False
        assert (
            len(node.get_addon_names()) ==
            addon_count
        )
