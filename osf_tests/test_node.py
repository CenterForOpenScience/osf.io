import datetime

from django.utils import timezone
import mock
import pytest
import pytz
import random
import string
from framework.celery_tasks import handlers
from framework.exceptions import PermissionsError
from framework.sessions import set_session
from website.project.model import has_anonymous_link
from website.project.signals import contributor_added, contributor_removed, after_create_registration
from website.exceptions import NodeStateError
from osf.utils import permissions
from website.util import api_url_for, web_url_for
from api_tests.utils import disconnected_from_listeners
from website.citations.utils import datetime_to_csl
from website import language, settings
from website.project.tasks import on_node_updated
from osf.utils.permissions import READ, WRITE, ADMIN, expand_permissions, DEFAULT_CONTRIBUTOR_PERMISSIONS

from osf.models import (
    AbstractNode,
    Node,
    Tag,
    NodeLog,
    Contributor,
    MetaSchema,
    Sanction,
    NodeRelation,
    Registration,
    DraftRegistration,
    DraftRegistrationApproval,
)
from osf.models.node import AbstractNodeQuerySet
from osf.models.spam import SpamStatus
from addons.wiki.models import NodeWikiPage
from osf.exceptions import ValidationError, ValidationValueError
from framework.auth.core import Auth

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    ProjectWithAddonFactory,
    NodeFactory,
    NodeLogFactory,
    UserFactory,
    UnregUserFactory,
    RegistrationFactory,
    DraftRegistrationFactory,
    PreprintFactory,
    NodeLicenseRecordFactory,
    PrivateLinkFactory,
    NodeRelationFactory,
    InstitutionFactory,
    SessionFactory,
    SubjectFactory,
    TagFactory,
)
from .factories import get_default_metaschema
from addons.wiki.tests.factories import NodeWikiFactory
from .utils import capture_signals, assert_datetime_equal, mock_archive, MockShareResponse

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)

@pytest.fixture()
def subject():
    return SubjectFactory()


class TestParentNode:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def child(self, project):
        return NodeFactory(parent=project, creator=project.creator)

    @pytest.fixture()
    def deleted_child(self, project):
        return NodeFactory(parent=project, creator=project.creator, is_deleted=True)

    @pytest.fixture()
    def registration(self, project):
        return RegistrationFactory(project=project)

    @pytest.fixture()
    def template(self, project, auth):
        return project.use_as_template(auth=auth)

    def test_top_level_node_has_parent_node_none(self):
        project = ProjectFactory()
        assert project.parent_node is None

    def test_component_has_parent_node(self):
        project = ProjectFactory()
        node = NodeFactory(parent=project)
        assert node.parent_node == project

    @pytest.mark.django_assert_num_queries
    def test_parent_node_is_cached_for_top_level_nodes(self, django_assert_num_queries):
        root = ProjectFactory()
        # Expect 0 queries because parent_node was already
        # accessed when creating the project_created log
        with django_assert_num_queries(0):
            root.parent_node
            root.parent_node

    def test_components_have_root(self):
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
    def test_root_for_linked_node_does_not_return_linking_parent(self):
        project = ProjectFactory(title='Project')
        root = ProjectFactory(title='Root')
        child = NodeFactory(title='Child', parent=root)

        project.add_node_link(root, auth=Auth(project.creator), save=True)
        assert root.root == root
        assert child.root == root

    def test_get_children(self):
        root = ProjectFactory()
        child = NodeFactory(parent=root)
        child1 = NodeFactory(parent=root)
        child2 = NodeFactory(parent=root)
        grandchild = NodeFactory(parent=child)
        grandchild1 = NodeFactory(parent=child)
        grandchild2 = NodeFactory(parent=child)
        grandchild3 = NodeFactory(parent=child)
        grandchild_1 = NodeFactory(parent=child1)
        for _ in range(0, 3):
            NodeFactory(parent=child1)
        for _ in range(0, 4):
            NodeFactory(parent=child2)

        NodeFactory(parent=grandchild)
        NodeFactory(parent=grandchild1)
        NodeFactory(parent=grandchild2)
        NodeFactory(parent=grandchild3)
        greatgrandchild_1 = NodeFactory(parent=grandchild_1, is_deleted=True)

        assert 20 == Node.objects.get_children(root).count()
        pks = Node.objects.get_children(root).values_list('id', flat=True)
        assert 20 == len(pks)
        assert set(pks) == set(Node.objects.exclude(id=root.id).values_list('id', flat=True))

        assert greatgrandchild_1 in Node.objects.get_children(root).all()
        assert greatgrandchild_1 not in Node.objects.get_children(root, active=True).all()

    def test_get_children_root_with_no_children(self):
        root = ProjectFactory()

        assert 0 == len(Node.objects.get_children(root))
        assert isinstance(Node.objects.get_children(root), AbstractNodeQuerySet)

    def test_get_children_child_with_no_children(self):
        root = ProjectFactory()
        child = ProjectFactory(parent=root)

        assert 0 == Node.objects.get_children(child).count()
        assert isinstance(Node.objects.get_children(child), AbstractNodeQuerySet)

    def test_get_children_with_nested_projects(self):
        root = ProjectFactory()
        child = NodeFactory(parent=root)
        grandchild = NodeFactory(parent=child)
        result = Node.objects.get_children(child)
        assert result.count() == 1
        assert grandchild in result

    def test_get_children_with_links(self):
        root = ProjectFactory()
        child = NodeFactory(parent=root)
        child1 = NodeFactory(parent=root)
        child2 = NodeFactory(parent=root)
        grandchild = NodeFactory(parent=child)
        grandchild1 = NodeFactory(parent=child)
        grandchild2 = NodeFactory(parent=child)
        grandchild3 = NodeFactory(parent=child)
        grandchild_1 = NodeFactory(parent=child1)
        for _ in range(0, 3):
            NodeFactory(parent=child1)
        for _ in range(0, 4):
            NodeFactory(parent=child2)

        NodeFactory(parent=grandchild)
        NodeFactory(parent=grandchild1)
        NodeFactory(parent=grandchild2)
        NodeFactory(parent=grandchild3)
        greatgrandchild_1 = NodeFactory(parent=grandchild_1)

        child.add_node_link(root, auth=Auth(root.creator))
        child.add_node_link(greatgrandchild_1, auth=Auth(greatgrandchild_1.creator))
        greatgrandchild_1.add_node_link(child, auth=Auth(child.creator))

        assert 20 == len(Node.objects.get_children(root))

    def test_get_roots(self):
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

    def test_get_roots_distinct(self):
        top_level = ProjectFactory()
        ProjectFactory(parent=top_level)
        ProjectFactory(parent=top_level)
        ProjectFactory(parent=top_level)

        assert AbstractNode.objects.get_roots().count() == 1
        assert top_level in AbstractNode.objects.get_roots()

    def test_license_searches_parent_nodes(self):
        license_record = NodeLicenseRecordFactory()
        project = ProjectFactory(node_license=license_record)
        node = NodeFactory(parent=project)
        assert project.license == license_record
        assert node.license == license_record

    def test_top_level_project_has_no_parent(self, project):
        assert project.parent_node is None

    def test_child_project_has_correct_parent(self, child, project):
        assert child.parent_node._id == project._id

    def test_grandchild_has_parent_of_child(self, child):
        grandchild = NodeFactory(parent=child, description='Spike')
        assert grandchild.parent_node._id == child._id

    def test_registration_has_no_parent(self, registration):
        assert registration.parent_node is None

    def test_registration_child_has_correct_parent(self, registration):
        registration_child = NodeFactory(parent=registration)
        assert registration._id == registration_child.parent_node._id

    def test_registration_grandchild_has_correct_parent(self, registration):
        registration_child = NodeFactory(parent=registration)
        registration_grandchild = NodeFactory(parent=registration_child)
        assert registration_grandchild.parent_node._id == registration_child._id

    def test_recursive_registrations_have_correct_root(self, project, auth):
        child = NodeFactory(parent=project)
        NodeFactory(parent=child)

        with disconnected_from_listeners(after_create_registration):
            reg_root = project.register_node(get_default_metaschema(), auth, '', None)
        reg_child = reg_root._nodes.first()
        reg_grandchild = reg_child._nodes.first()

        assert reg_root.root == reg_root
        assert reg_child.root == reg_root
        assert reg_grandchild.root == reg_root

    def test_fork_has_no_parent(self, project, auth):
        fork = project.fork_node(auth=auth)
        assert fork.parent_node is None

    def test_fork_child_has_parent(self, project, auth):
        fork = project.fork_node(auth=auth)
        fork_child = NodeFactory(parent=fork)
        assert fork_child.parent_node._id == fork._id

    def test_fork_grandchild_has_child_id(self, project, auth):
        fork = project.fork_node(auth=auth)
        fork_child = NodeFactory(parent=fork)
        fork_grandchild = NodeFactory(parent=fork_child)
        assert fork_grandchild.parent_node._id == fork_child._id

    def test_recursive_forks_have_correct_root(self, project, auth):
        child = NodeFactory(parent=project)
        NodeFactory(parent=child)

        fork_root = project.fork_node(auth=auth)
        fork_child = fork_root._nodes.first()
        fork_grandchild = fork_child._nodes.first()

        assert fork_root.root == fork_root
        assert fork_child.root == fork_root
        assert fork_grandchild.root == fork_root

    def test_template_has_no_parent(self, template):
        assert template.parent_node is None

    def test_teplate_project_child_has_correct_parent(self, template):
        template_child = NodeFactory(parent=template)
        assert template_child.parent_node._id == template._id

    def test_template_project_grandchild_has_correct_root(self, template):
        template_child = NodeFactory(parent=template)
        new_project_grandchild = NodeFactory(parent=template_child)
        assert new_project_grandchild.parent_node._id == template_child._id

    def test_recursive_templates_have_correct_root(self, project, auth):
        child = NodeFactory(parent=project)
        NodeFactory(parent=child)

        template_root = project.use_as_template(auth=auth)
        template_child = template_root._nodes.first()
        template_grandchild = template_child._nodes.first()

        assert template_root.root == template_root
        assert template_child.root == template_root
        assert template_grandchild.root == template_root

    def test_template_project_does_not_copy_deleted_components(self, project, child, deleted_child, template):
        """Regression test for https://openscience.atlassian.net/browse/OSF-5942. """
        new_nodes = [node.title for node in template.nodes]
        assert len(template.nodes) == 1
        assert deleted_child.title not in new_nodes

    def test_parent_node_doesnt_return_link_parent(self, project):
        linker = ProjectFactory(title='Linker')
        linker.add_node_link(project, auth=Auth(linker.creator), save=True)
        # Prevent cached parent_node property from being used
        project = Node.objects.get(id=project.id)
        assert project.parent_node is None


class TestRoot:
    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def registration(self, project):
        return RegistrationFactory(project=project)

    def test_top_level_project_has_own_root(self, project):
        assert project.root._id == project._id

    def test_child_project_has_root_of_parent(self, project):
        child = NodeFactory(parent=project)
        assert child.root._id == project._id
        assert child.root._id == project.root._id

    def test_grandchild_root_relationships(self, project):
        child_node_one = NodeFactory(parent=project)
        child_node_two = NodeFactory(parent=project)
        grandchild_from_one = NodeFactory(parent=child_node_one)
        grandchild_from_two = NodeFactory(parent=child_node_two)

        assert child_node_one.root._id == child_node_two.root._id
        assert grandchild_from_one.root._id == grandchild_from_two.root._id
        assert grandchild_from_two.root._id == project.root._id

    def test_grandchild_has_root_of_immediate_parent(self, project):
        child_node = NodeFactory(parent=project)
        grandchild_node = NodeFactory(parent=child_node)
        assert child_node.root._id == grandchild_node.root._id

    def test_registration_has_own_root(self, registration):
        assert registration.root._id == registration._id

    def test_registration_children_have_correct_root(self, registration):
        registration_child = NodeFactory(parent=registration)
        assert registration_child.root._id == registration._id

    def test_registration_grandchildren_have_correct_root(self, registration):
        registration_child = NodeFactory(parent=registration)
        registration_grandchild = NodeFactory(parent=registration_child)

        assert registration_grandchild.root._id == registration._id

    def test_fork_has_own_root(self, project, auth):
        fork = project.fork_node(auth=auth)
        fork.save()
        assert fork.root._id == fork._id

    def test_fork_children_have_correct_root(self, project, auth):
        fork = project.fork_node(auth=auth)
        fork_child = NodeFactory(parent=fork)
        assert fork_child.root._id == fork._id

    def test_fork_grandchildren_have_correct_root(self, project, auth):
        fork = project.fork_node(auth=auth)
        fork_child = NodeFactory(parent=fork)
        fork_grandchild = NodeFactory(parent=fork_child)
        assert fork_grandchild.root._id == fork._id

    def test_template_project_has_own_root(self, project, auth):
        new_project = project.use_as_template(auth=auth)
        assert new_project.root._id == new_project._id

    def test_template_project_child_has_correct_root(self, project, auth):
        new_project = project.use_as_template(auth=auth)
        new_project_child = NodeFactory(parent=new_project)
        assert new_project_child.root._id == new_project._id

    def test_template_project_grandchild_has_correct_root(self, project, auth):
        new_project = project.use_as_template(auth=auth)
        new_project_child = NodeFactory(parent=new_project)
        new_project_grandchild = NodeFactory(parent=new_project_child)
        assert new_project_grandchild.root._id == new_project._id

    def test_node_find_returns_correct_nodes(self, project):
        # Build up a family of nodes
        child_node_one = NodeFactory(parent=project)
        child_node_two = NodeFactory(parent=project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)
        # Create a rogue node that's not related at all
        NodeFactory()

        family_ids = [project._id] + [r._id for r in project.get_descendants_recursive()]
        family_nodes = Node.objects.filter(root=project)
        number_of_nodes = family_nodes.count()

        assert number_of_nodes == 5
        found_ids = []
        for node in family_nodes:
            assert node._id in family_ids
            found_ids.append(node._id)
        for node_id in family_ids:
            assert node_id in found_ids

    def test_get_descendants_recursive_returns_in_depth_order(self, project):
        """Test the get_descendants_recursive function to make sure its
        not returning any new nodes that we're not expecting
        """
        child_node_one = NodeFactory(parent=project)
        child_node_two = NodeFactory(parent=project)
        NodeFactory(parent=child_node_one)
        NodeFactory(parent=child_node_two)

        parent_list = [project._id]
        # Verifies, for every node in the list, that parent, we've seen before, in order.
        for p in project.get_descendants_recursive():
            parent_list.append(p._id)
            if p.parent_node:
                assert p.parent_node._id in parent_list


class TestNodeMODMCompat:

    def test_basic_querying(self):
        node_1 = ProjectFactory(is_public=False)
        node_2 = ProjectFactory(is_public=True)

        assert Node.objects.all().count() == 2

        private = Node.objects.filter(is_public=False)
        assert node_1 in private
        assert node_2 not in private

    def test_compound_query(self):
        node = NodeFactory(is_public=True, title='foo')

        assert node in Node.objects.filter(is_public=True, title='foo')
        assert node not in Node.objects.filter(is_public=False, title='foo')

    def test_title_validation(self):
        node = NodeFactory.build(title='')
        with pytest.raises(ValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['This field cannot be blank.']}

        too_long = 'a' * 201
        node = NodeFactory.build(title=too_long)
        with pytest.raises(ValidationError) as excinfo:
            node.save()
        assert excinfo.value.message_dict == {'title': ['Title cannot exceed 200 characters.']}

    def test_querying_on_guid_id(self):
        node = NodeFactory()
        assert len(node._id) == 5
        assert node in Node.objects.filter(guids___id=node._id)


# copied from tests/test_models.py
class TestProject:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user, description='foobar')

    @pytest.fixture()
    def child(self, user, project):
        return ProjectFactory(creator=user, description='barbaz', parent=project)

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

    def test_web_url_for(self, node, request_context):
        result = node.web_url_for('view_project')
        assert result == web_url_for(
            'view_project',
            pid=node._id,
        )

    def test_web_url_for_absolute(self, node, request_context):
        result = node.web_url_for('view_project', _absolute=True)
        assert settings.DOMAIN in result

    def test_api_url_for(self, node, request_context):
        result = node.api_url_for('view_project')
        assert result == api_url_for(
            'view_project',
            pid=node._id
        )

    def test_api_url_for_absolute(self, node, request_context):
        result = node.api_url_for('view_project', _absolute=True)
        assert settings.DOMAIN in result

    def test_get_absolute_url(self, node):
        assert node.get_absolute_url() == '{}v2/nodes/{}/'.format(settings.API_DOMAIN, node._id)

    def test_parents(self):
        node = ProjectFactory()
        child1 = ProjectFactory(parent=node)
        child2 = ProjectFactory(parent=child1)
        assert node.parents == []
        assert child1.parents == [node]
        assert child2.parents == [child1, node]

    def test_no_parent(self):
        node = ProjectFactory()
        assert node.parent_node is None

    def test_node_factory(self):
        node = NodeFactory()
        assert node.category == 'hypothesis'
        assert bool(node.parents)
        assert node.logs.first().action == 'project_created'
        assert set(node.get_addon_names()) == set([
            addon_config.short_name
            for addon_config in settings.ADDONS_AVAILABLE
            if 'node' in addon_config.added_default
        ])
        for addon_config in settings.ADDONS_AVAILABLE:
            if 'node' in addon_config.added_default:
                assert addon_config.short_name in node.get_addon_names()
                assert len([
                    addon
                    for addon in node.addons
                    if addon.config.short_name == addon_config.short_name
                ])

    def test_project_factory(self):
        node = ProjectFactory()
        assert node.category == 'project'
        assert bool(node._id)
        # assert_almost_equal(
        #     node.created, timezone.now(),
        #     delta=datetime.timedelta(seconds=5),
        # )
        assert node.is_public is False
        assert node.is_deleted is False
        assert hasattr(node, 'deleted_date')
        assert node.is_registration is False
        assert hasattr(node, 'registered_date')
        assert node.is_fork is False
        assert hasattr(node, 'forked_date')
        assert bool(node.title)
        assert hasattr(node, 'description')
        assert hasattr(node, 'registered_meta')
        assert hasattr(node, 'registered_user')
        assert hasattr(node, 'registered_schema')
        assert bool(node.creator)
        assert bool(node.contributors)
        assert node.logs.count() == 1
        assert hasattr(node, 'tags')
        assert hasattr(node, 'nodes')
        assert hasattr(node, 'forked_from')
        assert hasattr(node, 'registered_from')
        assert node.logs.latest().action == 'project_created'

    def test_parent_id(self, project, child):
        assert child.parent_id == project._id

    def test_parent(self, project, child):
        assert child.parent_node == project

    def test_in_parent_nodes(self, project, child):
        assert child in project.nodes

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

        # updates node.modified
        assert_datetime_equal(node.modified, last_log.date)


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

        tag = Tag.all_tags.get(name='FoO', system=True)
        assert node.all_tags.count() == 1
        assert tag in node.all_tags.all()

        assert tag.system is True

        # No log added
        new_log_count = node.logs.count()
        assert original_log_count == new_log_count

    def test_add_system_tag_instance(self, node):
        tag = TagFactory(system=True)
        node.add_system_tag(tag)

        assert tag in node.all_tags.all()

    def test_add_system_tag_non_system_instance(self, node):
        tag = TagFactory(system=False)
        with pytest.raises(ValueError):
            node.add_system_tag(tag)

        assert tag not in node.all_tags.all()

    def test_system_tags_property(self, node, auth):
        other_node = ProjectFactory()
        other_node.add_system_tag('bAr')

        node.add_system_tag('FoO')
        node.add_tag('bAr', auth=auth)

        assert 'FoO' in node.system_tags
        assert 'bAr' not in node.system_tags

    def test_system_tags_property_on_registration(self):
        project = ProjectFactory()
        project.add_system_tag('from-project')
        registration = RegistrationFactory(project=project)

        registration.add_system_tag('registration-only')

        # Registration gets project's system tags
        assert 'from-project' in registration.system_tags
        assert 'registration-only' not in project.system_tags
        assert 'registration-only' in registration.system_tags

    def test_tags_does_not_return_system_tags(self, node):
        node.add_system_tag('systag')
        assert 'systag' not in node.tags.values_list('name', flat=True)

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
        assert_datetime_equal(first_log.date, node.created)

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

    def test_can_view_public(self, project, auth):
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        project.add_contributor(
            contributor=contributor, auth=auth)
        # Change project to public
        project.set_privacy('public')
        project.save()
        # Creator, contributor, and noncontributor can view
        assert project.can_view(auth)
        assert project.can_view(contributor_auth)
        assert project.can_view(other_guy_auth)

    def test_is_fork_of(self, project):
        fork1 = project.fork_node(auth=Auth(user=project.creator))
        fork2 = fork1.fork_node(auth=Auth(user=project.creator))
        assert fork1.is_fork_of(project) is True
        assert fork2.is_fork_of(project) is True

    def test_is_fork_of_false(self, project):
        to_fork = ProjectFactory()
        fork = to_fork.fork_node(auth=Auth(user=to_fork.creator))
        assert fork.is_fork_of(project) is False

    def test_is_fork_of_no_forked_from(self, project):
        project2 = ProjectFactory()
        assert project2.is_fork_of(project) is False

    def test_is_registration_of(self, project):
        with mock_archive(project) as reg1:
            assert reg1.is_registration_of(project) is True

    def test_is_registration_of_false(self, project):
        to_reg = ProjectFactory()
        with mock_archive(to_reg) as reg:
            assert reg.is_registration_of(project) is False

    def test_raises_permissions_error_if_not_a_contributor(self, project):
        user = UserFactory()
        with pytest.raises(PermissionsError):
            project.register_node(None, Auth(user=user), '', None)

    def test_admin_can_register_private_children(self, project, user, auth):
        project.set_permissions(user, ['admin', 'write', 'read'])
        child = NodeFactory(parent=project, is_public=False)
        assert child.can_edit(auth=auth) is False  # sanity check
        with mock_archive(project, None, auth, '', None) as registration:
            # child was registered
            child_registration = registration.nodes[0]
            assert child_registration.registered_from == child

    def test_is_registration_of_no_registered_from(self, project):
        project2 = ProjectFactory()
        assert project2.is_registration_of(project) is False

    def test_registration_preserves_license(self, project):
        license = NodeLicenseRecordFactory()
        project.node_license = license
        project.save()
        with mock_archive(project, autocomplete=True) as registration:
            assert registration.node_license.license_id == license.license_id

    def test_is_contributor_unregistered(self, project, auth):
        unreg = UnregUserFactory()
        project.add_unregistered_contributor(
            fullname='David Davidson',
            email=unreg.username,
            auth=auth
        )
        project.save()
        assert project.is_contributor(unreg) is True

# Copied from tests/test_models
# Permissions are now on the Contributor model, and are well-defined (i.e. not 'dance')
# Consider removing this class
@pytest.mark.skip
class TestPermissions:

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    def test_default_creator_permissions(self, project):
        assert set(permissions.CREATOR_PERMISSIONS) == set(project.permissions[project.creator._id])

    def test_default_contributor_permissions(self, project):
        user = UserFactory()
        project.add_contributor(user, permissions=['read'], auth=Auth(user=project.creator))
        project.save()
        assert set(['read']) == set(self.project.get_permissions(user))

    def test_adjust_permissions(self, project):
        project.permissions[42] = ['dance']
        project.save()
        assert 42 not in self.project.permissions

    def test_add_permission(self, project):
        project.add_permission(project.creator, 'dance')
        assert project.creator._id in project.permissions
        assert 'dance' in project.permissions[project.creator._id]

    def test_add_permission_already_granted(self, project):
        project.add_permission(project.creator, 'dance')
        with pytest.raises(ValueError):
            project.add_permission(project.creator, 'dance')

    def test_remove_permission(self, project):
        project.add_permission(project.creator, 'dance')
        project.remove_permission(project.creator, 'dance')
        assert 'dance' not in project.permissions[project.creator._id]

    def test_remove_permission_not_granted(self, project):
        with pytest.raises(ValueError):
            project.remove_permission(project.creator, 'dance')

    def test_has_permission_true(self, project):
        project.add_permission(project.creator, 'dance')
        assert project.has_permission(project.creator, 'dance') is True

    def test_has_permission_false(self, project):
        project.add_permission(project.creator, 'dance')
        assert project.has_permission(self.project.creator, 'sing') is False

    def test_has_permission_not_in_dict(self, project):
        assert project.has_permission(project.creator, 'dance') is False


class TestNodeSubjects:

    @pytest.fixture()
    def write_contrib(self, project):
        write_contrib = AuthUserFactory()
        project.add_contributor(write_contrib, auth=Auth(project.creator), permissions=(READ, WRITE))
        project.save()
        return write_contrib

    def test_nonadmin_cannot_set_subjects(self, project, subject, write_contrib):
        initial_subjects = list(project.subjects.all())
        with pytest.raises(PermissionsError):
            project.set_subjects([[subject._id]], auth=Auth(write_contrib))

        project.reload()
        assert initial_subjects == list(project.subjects.all())

    def test_admin_can_set_subjects(self, project, subject):
        initial_subjects = list(project.subjects.all())
        project.set_subjects([[subject._id]], auth=Auth(project.creator))

        project.reload()
        assert initial_subjects != list(project.subjects.all())


class TestRegisterNode:

    def test_register_node_creates_new_registration(self, node, auth):
        with disconnected_from_listeners(after_create_registration):
            registration = node.register_node(get_default_metaschema(), auth, '', None)
            assert type(registration) is Registration
            assert node._id != registration._id

    def test_cannot_register_deleted_node(self, node, auth):
        node.is_deleted = True
        node.save()
        with pytest.raises(NodeStateError) as err:
            node.register_node(
                schema=None,
                auth=auth,
                data=None
            )
        assert err.value.message == 'Cannot register deleted node.'

    @mock.patch('website.project.signals.after_create_registration')
    def test_register_node_copies_subjects(self, mock_signal, subject):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.is_public = True
        node.set_subjects([[subject._id]], auth=Auth(user))
        node.save()
        registration = node.register_node(get_default_metaschema(), Auth(user), '', None)
        assert registration.subjects.filter(id=subject.id).exists()

    @mock.patch('website.project.signals.after_create_registration')
    def test_register_node_makes_private_registration(self, mock_signal):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.is_public = True
        node.save()
        registration = node.register_node(get_default_metaschema(), Auth(user), '', None)
        assert registration.is_public is False

    @mock.patch('website.project.signals.after_create_registration')
    def test_register_node_makes_private_child_registrations(self, mock_signal):
        user = UserFactory()
        node = NodeFactory(creator=user)
        node.is_public = True
        node.save()
        child = NodeFactory(parent=node)
        child.is_public = True
        child.save()
        childchild = NodeFactory(parent=child)
        childchild.is_public = True
        childchild.save()
        registration = node.register_node(get_default_metaschema(), Auth(user), '', None)
        for node in registration.node_and_primary_descendants():
            assert node.is_public is False

    @mock.patch('website.project.signals.after_create_registration')
    def test_register_node_propagates_schema_and_data_to_children(self, mock_signal, user, auth):
        root = ProjectFactory(creator=user)
        c1 = ProjectFactory(creator=user, parent=root)
        ProjectFactory(creator=user, parent=c1)

        meta_schema = MetaSchema.objects.get(name='Open-Ended Registration', schema_version=1)

        data = {'some': 'data'}
        reg = root.register_node(
            schema=meta_schema,
            auth=auth,
            data=data,
        )
        r1 = reg.nodes[0]
        r1a = r1.nodes[0]
        for r in [reg, r1, r1a]:
            assert r.registered_meta[meta_schema._id] == data
            assert r.registered_schema.first() == meta_schema


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

    private_node = NodeFactory(is_public=False)
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

    @mock.patch('osf.models.queued_mail.queue_mail')
    def test_set_privacy_sends_mail_default(self, mock_queue, node, auth):
        node.set_privacy('private', auth=auth)
        node.set_privacy('public', auth=auth)
        assert mock_queue.call_count == 1

    @mock.patch('osf.models.queued_mail.queue_mail')
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
class TestNodeSpam:

    @pytest.fixture()
    def project(self):
        return ProjectFactory(is_public=True)

    @mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', True)
    def test_set_privacy_on_spammy_node(self, project):
        project.is_public = False
        project.save()
        with mock.patch.object(Node, 'is_spammy', mock.PropertyMock(return_value=True)):
            with pytest.raises(NodeStateError):
                project.set_privacy('public')

    def test_check_spam_disabled_by_default(self, project, user):
        # SPAM_CHECK_ENABLED is False by default
        with mock.patch('osf.models.node.Node._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.node.Node.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                project.set_privacy('public')
                assert project.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_check_spam_only_public_node_by_default(self, project, user):
        # SPAM_CHECK_PUBLIC_ONLY is True by default
        with mock.patch('osf.models.node.Node._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.node.Node.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                project.set_privacy('private')
                assert project.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_check_spam_skips_ham_user(self, project, user):
        with mock.patch('osf.models.AbstractNode._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.AbstractNode.do_check_spam', mock.Mock(side_effect=Exception('should not get here'))):
                user.add_system_tag('ham_confirmed')
                project.set_privacy('public')
                assert project.check_spam(user, None, None) is False

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_CHECK_PUBLIC_ONLY', False)
    def test_check_spam_on_private_node(self, project, user):
        project.is_public = False
        project.save()
        with mock.patch('osf.models.node.Node._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.node.Node.do_check_spam', mock.Mock(return_value=True)):
                project.set_privacy('private')
                assert project.check_spam(user, None, None) is True

    @mock.patch('osf.models.node.mails.send_mail')
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_ACCOUNT_SUSPENSION_ENABLED', True)
    def test_check_spam_on_private_node_bans_new_spam_user(self, mock_send_mail, project, user):
        project.is_public = False
        project.save()
        with mock.patch('osf.models.AbstractNode._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.AbstractNode.do_check_spam', mock.Mock(return_value=True)):
                user.date_confirmed = timezone.now()
                project.set_privacy('public')
                user2 = UserFactory()
                # project w/ one contributor
                project2 = ProjectFactory(creator=user, description='foobar2', is_public=True)
                project2.save()
                # project with more than one contributor
                project3 = ProjectFactory(creator=user, description='foobar3', is_public=True)
                project3.add_contributor(user2)
                project3.save()

                assert project.check_spam(user, None, None) is True

                assert user.is_disabled is True
                assert project.is_public is False
                project2.reload()
                assert project2.is_public is False
                project3.reload()
                assert project3.is_public is True

    @mock.patch('osf.models.node.mails.send_mail')
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_ACCOUNT_SUSPENSION_ENABLED', True)
    def test_check_spam_on_private_node_does_not_ban_existing_user(self, mock_send_mail, project, user):
        project.is_public = False
        project.save()
        with mock.patch('osf.models.AbstractNode._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.AbstractNode.do_check_spam', mock.Mock(return_value=True)):
                project.creator.date_confirmed = timezone.now() - datetime.timedelta(days=9001)
                project.set_privacy('public')
                assert project.check_spam(user, None, None) is True
                assert project.is_public is True

    def test_flag_spam_make_node_private(self, project):
        assert project.is_public
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', True):
            project.flag_spam()
        assert project.is_spammy
        assert project.is_public is False

    def test_flag_spam_do_not_make_node_private(self, project):
        assert project.is_public
        with mock.patch.object(settings, 'SPAM_FLAGGED_MAKE_NODE_PRIVATE', False):
            project.flag_spam()
        assert project.is_spammy
        assert project.is_public

    def test_confirm_spam_makes_node_private(self, project):
        assert project.is_public
        project.confirm_spam()
        assert project.is_spammy
        assert project.is_public is False


# copied from tests/test_models.py
class TestPrivateLinks:
    def test_add_private_link(self, node):
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        assert link in node.private_links.all()

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_has_anonymous_link(self, mock_property, node):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = True

        link1 = PrivateLinkFactory(key='link1')
        link1.nodes.add(node)
        link1.save()

        user2 = UserFactory()
        auth2 = Auth(user=user2, private_key='link1')

        assert has_anonymous_link(node, auth2) is True

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_has_no_anonymous_link(self, mock_property, node):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = False

        link2 = PrivateLinkFactory(key='link2')
        link2.nodes.add(node)
        link2.save()

        user3 = UserFactory()
        auth3 = Auth(user=user3, private_key='link2')

        assert has_anonymous_link(node, auth3) is False

    def test_node_scale(self):
        link = PrivateLinkFactory()
        project = ProjectFactory()
        comp = NodeFactory(parent=project)
        link.nodes.add(project)
        link.save()
        assert link.node_scale(project) == -40
        assert link.node_scale(comp) == -20

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_to_json_nodes_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(parent=project)
        link.nodes.add(project)
        link.nodes.add(node)
        link.save()
        result = link.to_json()
        # result doesn't include deleted parent
        assert len(result['nodes']) == 1

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_node_scale_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = ProjectFactory(is_deleted=True)
        node = NodeFactory(parent=project)
        link.nodes.add(project)
        link.nodes.add(node)
        link.save()
        assert link.node_scale(node) == -40

    # TODO: This seems like it should go elsewhere, but was in tests/test_models.py::TestPrivateLink
    def test_create_from_node(self):
        proj = ProjectFactory()
        user = proj.creator
        schema = MetaSchema.objects.first()
        data = {'some': 'data'}
        draft = DraftRegistration.create_from_node(
            proj,
            user=user,
            schema=schema,
            data=data,
        )
        assert user == draft.initiator
        assert schema == draft.registration_schema
        assert data == draft.registration_metadata
        assert proj == draft.branched_from


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

    def test_contributor_set_visibility_validation(self, node, user, auth):
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        node.add_contributors(
            [
                {'user': reg_user1, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': [
                    'read', 'write', 'admin'], 'visible': False},
            ]
        )
        print(node.visible_contributor_ids)
        with pytest.raises(ValueError) as e:
            node.set_visible(user=reg_user1, visible=False, auth=None)
            node.set_visible(user=user, visible=False, auth=None)
            assert e.value.message == 'Must have at least one visible contributor'

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

    def test_manage_contributors_no_admins(self, node, auth):
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

    def test_get_admin_contributors(self, user, auth):
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
        assert Node.objects.filter(guids___id__in=reg_ids, is_deleted=False).count() == 0
        assert mock_update_search.call_count == orig_call_count + len(reg_ids)

    def test_delete_registration_tree_sets_draft_registration_approvals_to_none(self, user):
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

    def test_linked_from(self, node, auth):
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
        assert NodeRelation.objects.filter(child=node2, is_node_link=True).count() == 0
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

    def test_cannot_fork_deleted_node(self, node, auth):
        child = NodeFactory(parent=node, is_deleted=True)
        child.save()
        fork = node.fork_node(auth=auth)
        assert not fork.nodes

    def test_cannot_template_deleted_node(self, node, auth):
        child = NodeFactory(parent=node, is_deleted=True)
        child.save()
        template = node.use_as_template(auth=auth, top_level=False)
        assert not template.nodes

    def _fork_pointer(self, node, content, auth):
        pointer = node.add_pointer(content, auth=auth)
        forked = node.fork_pointer(pointer, auth=auth)
        assert forked.is_fork is True
        assert forked.forked_from == content
        assert forked.primary is True
        assert(
            node.logs.latest().action == NodeLog.POINTER_FORKED
        )
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
        assert (fork_date - fork.created) < datetime.timedelta(seconds=30)
        assert fork.forked_date != original.created

        # Test that pointers were copied correctly
        assert(
            list(original.nodes_pointer.all()) == list(fork.nodes_pointer.all())
        )

        # Test that subjects were copied correctly
        assert(
            list(original.subjects.all()) == list(fork.subjects.all())
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
    def test_fork_recursion(self, mock_push_status_message, project, user, subject, auth, request_context):
        """Omnibus test for forking.
        """
        # Make some children
        component = NodeFactory(creator=user, parent=project)
        subproject = ProjectFactory(creator=user, parent=project)

        # Add pointers to test copying
        pointee = ProjectFactory()
        project.add_pointer(pointee, auth=auth)
        component.add_pointer(pointee, auth=auth)
        subproject.add_pointer(pointee, auth=auth)

        # Add add-on to test copying
        project.add_addon('dropbox', auth)
        component.add_addon('dropbox', auth)
        subproject.add_addon('dropbox', auth)

        # Add subject to test copying
        project.set_subjects([[subject._id]], auth)

        # Log time
        fork_date = timezone.now()

        # Fork node
        with mock.patch.object(Node, 'bulk_update_search'):
            fork = project.fork_node(auth=auth)

        # Compare fork to original
        self._cmp_fork_original(user, fork_date, fork, project)

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

        node.move_contributor(user2, auth=auth, index=0, save=True)

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
    result = Node.objects.filter(_contributors=user)
    assert node in result
    assert deleted in result

    result2 = Node.objects.filter(_contributors=user, is_deleted=False)
    assert node in result2
    assert deleted not in result2


class TestDOIValidation:

    def test_validate_bad_doi(self):
        with pytest.raises(ValidationError):
            Node(preprint_article_doi='nope').save()
        with pytest.raises(ValidationError):
            Node(preprint_article_doi='https://dx.doi.org/10.123.456').save()  # should save the bare DOI, not a URL
        with pytest.raises(ValidationError):
            Node(preprint_article_doi='doi:10.10.1038/nwooo1170').save()  # should save without doi: prefix

    def test_validate_good_doi(self, node):
        doi = '10.11038/nwooo1170'
        node.preprint_article_doi = doi
        node.save()
        assert node.preprint_article_doi == doi


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
    def test_get_aggregate_logs_queryset_doesnt_return_hidden_logs(self, parent, auth):
        n_orig_logs = len(parent.get_aggregate_logs_queryset(auth))

        log = parent.logs.latest()
        log.should_hide = True
        log.save()

        n_new_logs = len(parent.get_aggregate_logs_queryset(auth))
        # Hidden log is not returned
        assert n_new_logs == n_orig_logs - 1

    def test_excludes_logs_for_linked_nodes(self, parent):
        pointee = ProjectFactory()
        n_logs_before = parent.get_aggregate_logs_queryset(auth=Auth(parent.creator)).count()
        parent.add_node_link(pointee, auth=Auth(parent.creator))
        n_logs_after = parent.get_aggregate_logs_queryset(auth=Auth(parent.creator)).count()
        # one more log for adding the node link
        assert n_logs_after == n_logs_before + 1

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
            contrib.csl_name(node._id) for contrib in [node.creator, visible]
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

    def test_set_title_works_with_valid_title(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        proj.set_title('This is now', auth=auth)
        proj.save()
        # Title was changed
        assert proj.title == 'This is now'
        # A log event was saved
        latest_log = proj.logs.latest()
        assert latest_log.action == 'edit_title'
        assert latest_log.params['title_original'] == 'That Was Then'

    def test_set_title_fails_if_empty_or_whitespace(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        with pytest.raises(ValidationValueError):
            proj.set_title(' ', auth=auth)
        with pytest.raises(ValidationValueError):
            proj.set_title('', auth=auth)
        assert proj.title == 'That Was Then'

    def test_set_title_fails_if_too_long(self, user, auth):
        proj = ProjectFactory(title='That Was Then', creator=user)
        long_title = ''.join('a' for _ in range(201))
        with pytest.raises(ValidationValueError):
            proj.set_title(long_title, auth=auth)

    def test_set_description(self, node, auth):
        old_desc = node.description
        node.set_description(
            'new description', auth=auth)
        node.save()
        assert node.description, 'new description'
        latest_log = node.logs.latest()
        assert latest_log.action, NodeLog.EDITED_DESCRIPTION
        assert latest_log.params['description_original'], old_desc
        assert latest_log.params['description_new'], 'new description'

    def test_validate_categories(self):
        with pytest.raises(ValidationError):
            Node(category='invalid').save()  # an invalid category

    def test_category_display(self):
        node = NodeFactory(category='hypothesis')
        assert node.category_display == 'Hypothesis'
        node2 = NodeFactory(category='methods and measures')
        assert node2.category_display == 'Methods and Measures'

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


class TestOnNodeUpdate:

    @pytest.fixture(autouse=True)
    def session(self, user, request_context):
        s = SessionFactory(user=user)
        set_session(s)
        return s

    @pytest.fixture()
    def node(self):
        return ProjectFactory(is_public=True)

    @pytest.fixture()
    def registration(self, node):
        return RegistrationFactory(is_public=True)

    def teardown_method(self, method):
        handlers.celery_before_request()

    @mock.patch('osf.models.node.enqueue_task')
    def test_enqueue_called(self, enqueue_task, node, user, request_context):
        node.title = 'A new title'
        node.save()

        (task, ) = enqueue_task.call_args[0]

        assert task.task == 'website.project.tasks.on_node_updated'
        assert task.args[0] == node._id
        assert task.args[1] == user._id
        assert task.args[2] is False
        assert 'title' in task.args[3]

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_updates_share(self, requests, node, user):
        on_node_updated(node._id, user._id, False, {'is_public'})

        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']

        assert requests.post.called
        assert kwargs['headers']['Authorization'] == 'Bearer Token'
        assert graph[0]['uri'] == '{}{}/'.format(settings.DOMAIN, node._id)

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_update_share_correctly_for_projects(self, requests, node, user, request_context):
        cases = [{
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': False, 'is_deleted': False, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': True, 'spam_status': SpamStatus.HAM}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': False, 'spam_status': SpamStatus.SPAM}
        }]

        for case in cases:
            for attr, value in case['attrs'].items():
                setattr(node, attr, value)
            node.save()

            on_node_updated(node._id, user._id, False, {'is_public'})

            kwargs = requests.post.call_args[1]
            graph = kwargs['json']['data']['attributes']['data']['@graph']
            assert graph[1]['is_deleted'] == case['is_deleted']

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_update_share_correctly_for_registrations(self, requests, registration, user, request_context):
        cases = [{
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': False, 'is_deleted': False}
        }, {
            'is_deleted': True,
            'attrs': {'is_public': True, 'is_deleted': True}
        }, {
            'is_deleted': False,
            'attrs': {'is_public': True, 'is_deleted': False}
        }]

        for case in cases:
            for attr, value in case['attrs'].items():
                setattr(registration, attr, value)
            registration.save()

            on_node_updated(registration._id, user._id, False, {'is_public'})

            assert registration.is_registration
            kwargs = requests.post.call_args[1]
            graph = kwargs['json']['data']['attributes']['data']['@graph']
            payload = (item for item in graph if 'is_deleted' in item.keys()).next()
            assert payload['is_deleted'] == case['is_deleted']

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_update_share_correctly_for_projects_with_qa_tags(self, requests, node, user, request_context):
        node.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        on_node_updated(node._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is True

        node.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)
        on_node_updated(node._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is False

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_update_share_correctly_for_registrations_with_qa_tags(self, requests, registration, user, request_context):
        registration.add_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user))
        on_node_updated(registration._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is True

        registration.remove_tag(settings.DO_NOT_INDEX_LIST['tags'][0], auth=Auth(user), save=True)
        on_node_updated(registration._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is False

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    def test_update_share_correctly_for_projects_with_qa_titles(self, requests, node, user, request_context):
        node.title = settings.DO_NOT_INDEX_LIST['titles'][0].join(random.choice(string.ascii_lowercase) for i in range(5))
        node.save()
        on_node_updated(node._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is True

        node.title = 'Not a qa title'
        node.save()
        assert node.title not in settings.DO_NOT_INDEX_LIST['titles']
        on_node_updated(node._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is False

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'https://share.osf.io')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'Token')
    @mock.patch('website.project.tasks.requests')
    @mock.patch('osf.models.registrations.Registration.archiving', mock.PropertyMock(return_value=False))
    def test_update_share_correctly_for_registrations_with_qa_titles(self, requests, registration, user, request_context):
        registration.title = settings.DO_NOT_INDEX_LIST['titles'][0].join(random.choice(string.ascii_lowercase) for i in range(5))
        registration.save()
        on_node_updated(registration._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is True

        registration.title = 'Not a qa title'
        registration.save()
        assert registration.title not in settings.DO_NOT_INDEX_LIST['titles']
        on_node_updated(registration._id, user._id, False, {'is_public'})
        kwargs = requests.post.call_args[1]
        graph = kwargs['json']['data']['attributes']['data']['@graph']
        payload = (item for item in graph if 'is_deleted' in item.keys()).next()
        assert payload['is_deleted'] is False

    @mock.patch('website.project.tasks.settings.SHARE_URL', None)
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', None)
    @mock.patch('website.project.tasks.requests')
    def test_skips_no_settings(self, requests, node, user, request_context):
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert requests.post.called is False

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'a_real_token')
    @mock.patch('website.project.tasks._async_update_node_share.delay')
    @mock.patch('website.project.tasks.requests')
    def test_call_async_update_on_500_failure(self, requests, mock_async, node, user, request_context):
        requests.post.return_value = MockShareResponse(501)
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert mock_async.called

    @mock.patch('website.project.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.project.tasks.settings.SHARE_API_TOKEN', 'a_real_token')
    @mock.patch('website.project.tasks.send_desk_share_error')
    @mock.patch('website.project.tasks._async_update_node_share.delay')
    @mock.patch('website.project.tasks.requests')
    def test_no_call_async_update_on_400_failure(self, requests, mock_async, mock_mail, node, user, request_context):
        requests.post.return_value = MockShareResponse(400)
        on_node_updated(node._id, user._id, False, {'is_public'})
        assert mock_mail.called
        assert not mock_async.called

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
        assert new.created != project.created
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
        assert new.created != project.created
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

    def test_can_template_a_registration(self, user, auth):
        registration = RegistrationFactory(creator=user)
        new = registration.use_as_template(auth=auth)
        assert new.is_registration is False

    def test_cannot_template_deleted_registration(self, project, auth):
        registration = RegistrationFactory(project=project, is_deleted=True)
        new = registration.use_as_template(auth=auth)
        assert not new.nodes

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

    def test_complex_template_without_pointee(self, auth, user):
        """Create a templated node from a node with children"""

        # create templated node
        project1 = ProjectFactory(creator=user)
        ProjectFactory(creator=user, parent=project1)

        new = project1.use_as_template(auth=auth)

        assert new.title == self._default_title(project1)
        assert len(list(new.nodes)) == len(list(project1.nodes))
        # check that all children were copied
        assert (
            [x.title for x in new.nodes] ==
            [x.title for x in project1.nodes if x not in project1.linked_nodes]
        )
        # ensure all child nodes were actually copied, instead of moved
        assert {x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in project1.nodes}
        )

    def test_complex_template_with_pointee(self, auth, project, pointee, component, subproject):
        """Create a templated node from a node with children"""

        # create templated node
        new = project.use_as_template(auth=auth)

        assert new.title == self._default_title(project)
        assert len(list(new.nodes)) == len(list(project.nodes)) - 1
        # check that all children were copied
        assert (
            [x.title for x in new.nodes] ==
            [x.title for x in project.nodes if x not in project.linked_nodes]
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
        old_nodes = [x for x in project.nodes if x not in project.linked_nodes]

        for old_node, new_node in zip(old_nodes, new.nodes):
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
            set(x._id for x in visible_nodes if x not in project.linked_nodes)
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
class TestNodeLog:

    @pytest.fixture()
    def log(self, node):
        return NodeLogFactory(node=node)

    def test_repr(self, log):
        rep = repr(log)
        assert log.action in rep
        assert log.user._id in rep
        assert log.node._id in rep

    def test_node_log_factory(self, log):
        assert bool(log.action)

    def test_tz_date(self, log):
        assert log.date.tzinfo == pytz.UTC

    def test_original_node_and_current_node_for_registration_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        registration = RegistrationFactory(project=project)

        log_project_created_original = project.logs.last()
        log_registration_initiated = project.logs.latest()
        log_project_created_registration = registration.logs.last()

        assert project._id == log_project_created_original.original_node._id
        assert project._id == log_project_created_original.node._id
        assert project._id == log_registration_initiated.original_node._id
        assert project._id == log_registration_initiated.node._id
        assert project._id == log_project_created_registration.original_node._id
        assert registration._id == log_project_created_registration.node._id

    def test_original_node_and_current_node_for_fork_logs(self):
        user = UserFactory()
        project = ProjectFactory(creator=user)
        fork = project.fork_node(auth=Auth(user))

        log_project_created_original = project.logs.last()
        log_project_created_fork = fork.logs.last()
        log_node_forked = fork.logs.latest()

        assert project._id == log_project_created_original.original_node._id
        assert project._id == log_project_created_original.node._id
        assert project._id == log_project_created_fork.original_node._id
        assert project._id == log_node_forked.original_node._id
        assert fork._id == log_project_created_fork.node._id
        assert fork._id == log_node_forked.node._id


class TestProjectWithAddons:

    def test_factory(self):
        p = ProjectWithAddonFactory(addon='s3')
        assert bool(p.get_addon('s3')) is True
        assert bool(p.creator.get_addon('s3')) is True


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

# copied from tests/test_models.py
class TestAddonCallbacks:
    """Verify that callback functions are called at the right times, with the
    right arguments.
    """

    callbacks = {
        'after_remove_contributor': None,
        'after_set_privacy': None,
        'after_fork': (None, None),
        'after_register': (None, None),
    }

    @pytest.fixture()
    def parent(self):
        return ProjectFactory()

    @pytest.fixture()
    def node(self, user, parent):
        return NodeFactory(creator=user, parent=parent)

    @pytest.fixture(autouse=True)
    def mock_addons(self, node):
        def mock_get_addon(addon_name, deleted=False):
            # Overrides AddonModelMixin.get_addon -- without backrefs,
            # no longer guaranteed to return the same set of objects-in-memory
            return self.patched_addons.get(addon_name, None)

        self.patches = []
        self.patched_addons = {}
        self.original_get_addon = Node.get_addon

        # Mock addon callbacks
        for addon in node.addons:
            mock_settings = mock.create_autospec(addon.__class__)
            for callback, return_value in self.callbacks.iteritems():
                mock_callback = getattr(mock_settings, callback)
                mock_callback.return_value = return_value
                patch = mock.patch.object(
                    addon,
                    callback,
                    getattr(mock_settings, callback)
                )
                patch.start()
                self.patches.append(patch)
            self.patched_addons[addon.config.short_name] = addon
        n_patch = mock.patch.object(
            node,
            'get_addon',
            mock_get_addon
        )
        n_patch.start()
        self.patches.append(n_patch)

    def teardown_method(self, method):
        for patcher in self.patches:
            patcher.stop()

    def test_remove_contributor_callback(self, node, auth):
        user2 = UserFactory()
        node.add_contributor(contributor=user2, auth=auth)
        node.remove_contributor(contributor=user2, auth=auth)
        for addon in node.addons:
            callback = addon.after_remove_contributor
            callback.assert_called_once_with(
                node, user2, auth
            )

    def test_set_privacy_callback(self, node, auth):
        node.set_privacy('public', auth)
        for addon in node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                node, 'public',
            )

        node.set_privacy('private', auth)
        for addon in node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                node, 'private'
            )

    def test_fork_callback(self, node, auth):
        fork = node.fork_node(auth=auth)
        for addon in node.addons:
            callback = addon.after_fork
            callback.assert_called_once_with(
                node, fork, auth.user
            )

    def test_register_callback(self, node, auth):
        with mock_archive(node) as registration:
            for addon in node.addons:
                callback = addon.after_register
                callback.assert_called_once_with(
                    node, registration, auth.user
                )


class TestAdminImplicitRead(object):

    @pytest.fixture()
    def jane_doe(self):
        return UserFactory()

    @pytest.fixture()
    def creator(self):
        return UserFactory()

    @pytest.fixture()
    def admin_user(self, project):
        user = UserFactory()
        project.add_contributor(user, permissions=['admin'], save=True)
        return user

    @pytest.fixture()
    def project(self, creator):
        return ProjectFactory(is_public=False, creator=creator)

    @pytest.fixture()
    def lvl1component(self, project):
        return ProjectFactory(is_public=False, parent=project)

    @pytest.fixture()
    def lvl2component(self, lvl1component):
        return ProjectFactory(is_public=False, parent=lvl1component)

    @pytest.fixture()
    def lvl3component(self, lvl2component):
        return ProjectFactory(is_public=False, parent=lvl2component)

    def test_direct_child(self, admin_user, lvl1component):
        assert Node.objects.filter(id=lvl1component.pk).can_view(admin_user).count() == 1
        assert Node.objects.filter(id=lvl1component.pk).can_view(admin_user)[0] == lvl1component

    def test_rando(self, lvl1component, jane_doe):
        assert Node.objects.filter(id=lvl1component.pk).can_view(jane_doe).count() == 0

    def test_includes_parent(self, project, admin_user, lvl1component):
        assert Node.objects.filter(
            id__in=[lvl1component.pk, project.pk]
        ).can_view(admin_user).count() == 2

    def test_includes_public(self, admin_user, project, lvl1component):
        proj = ProjectFactory(is_public=True)

        qs = Node.objects.can_view(admin_user)

        assert proj in qs
        assert project in qs
        assert lvl1component in qs

    def test_empty_is_public(self):
        proj = ProjectFactory(is_public=True)

        qs = Node.objects.can_view()

        assert proj in qs
        assert qs.count() == 1

    def test_generations(self, admin_user, project, lvl1component, lvl2component, lvl3component):
        qs = Node.objects.can_view(admin_user)

        assert project in qs
        assert lvl1component in qs
        assert lvl2component in qs
        assert lvl3component in qs

    def test_private_link(self, jane_doe, project, lvl1component):
        pl = PrivateLinkFactory()
        lvl1component.private_links.add(pl)

        qs = Node.objects.can_view(user=jane_doe, private_link=pl)

        assert lvl1component in qs
        assert project not in qs


class TestPreprintProperties:

    def test_preprint_url_does_not_return_unpublished_preprint_url(self):
        node = ProjectFactory(is_public=True)
        published = PreprintFactory(project=node, is_published=True, filename='file1.txt')
        PreprintFactory(project=node, is_published=False, filename='file2.txt')
        assert node.preprint_url == published.url
