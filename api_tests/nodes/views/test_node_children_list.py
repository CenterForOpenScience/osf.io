import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import AbstractNode, NodeLog
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)
from tests.base import fake
from website.util import permissions
from website.util.sanitize import strip_html


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestNodeChildrenList:

    @pytest.fixture()
    def private_project(self, user):
        private_project = ProjectFactory()
        private_project.add_contributor(user, permissions=[permissions.READ, permissions.WRITE])
        private_project.save()
        return private_project

    @pytest.fixture()
    def component(self, user, private_project):
        return NodeFactory(parent=private_project, creator=user)

    @pytest.fixture()
    def pointer(self):
        return ProjectFactory()

    @pytest.fixture()
    def private_project_url(self, private_project):
        return '/{}nodes/{}/children/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_component(self, user, public_project):
        return NodeFactory(parent=public_project, creator=user, is_public=True)

    @pytest.fixture()
    def public_project_url(self, user, public_project):
        return '/{}nodes/{}/children/'.format(API_BASE, public_project._id)

    def test_return_public_node_children_list(self, app, public_project, public_component, public_project_url):

    # test_return_public_node_children_list_logged_out
        res = app.get(public_project_url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == public_component._id

    # test_return_public_node_children_list_logged_in
        non_contrib = AuthUserFactory()
        res = app.get(public_project_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == public_component._id

    def test_return_private_node_children_list(self, app, user, component, private_project_url):

    #   test_return_private_node_children_list_logged_out
        res = app.get(private_project_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_node_children_list_logged_in_non_contributor
        non_contrib = AuthUserFactory()
        res = app.get(private_project_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_node_children_list_logged_in_contributor
        res = app.get(private_project_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == component._id

    def test_node_children_list_does_not_include_pointers(self, app, user, component, private_project_url):
        res = app.get(private_project_url, auth=user.auth)
        assert len(res.json['data']) == 1

    def test_node_children_list_does_not_include_unauthorized_projects(self, app, user, component, private_project, private_project_url):
        private_component = NodeFactory(parent=private_project)
        res = app.get(private_project_url, auth=user.auth)
        assert len(res.json['data']) == 1

    def test_node_children_list_does_not_include_deleted(self, app, user, public_project, public_component, component, public_project_url):
        child_project = NodeFactory(parent=public_project, creator=user)
        child_project.save()

        res = app.get(public_project_url, auth=user.auth)
        assert res.status_code == 200
        ids = [node['id'] for node in res.json['data']]
        assert child_project._id in ids
        assert 2 == len(ids)

        child_project.is_deleted = True
        child_project.save()

        res = app.get(public_project_url, auth=user.auth)
        assert res.status_code == 200
        ids = [node['id'] for node in res.json['data']]
        assert child_project._id not in ids
        assert 1 == len(ids)

    def test_node_children_list_does_not_include_node_links(self, app, user, public_project, private_project, public_component, component, pointer, public_project_url):
        pointed_to = ProjectFactory(is_public=True)

        public_project.add_pointer(pointed_to, auth=Auth(public_project.creator))

        res = app.get(public_project_url, auth=user.auth)
        ids = [node['id'] for node in res.json['data']]
        assert public_component._id in ids  # sanity check

        assert pointed_to._id not in ids


@pytest.mark.django_db
class TestNodeChildrenListFiltering:

    def test_node_child_filtering(self, app, user):
        project = ProjectFactory(creator=user)

        title_one, title_two = fake.bs(), fake.bs()
        component = NodeFactory(title=title_one, parent=project)
        component_two = NodeFactory(title=title_two, parent=project)

        url = '/{}nodes/{}/children/?filter[title]={}'.format(
            API_BASE,
            project._id,
            title_one
        )
        res = app.get(url, auth=user.auth)

        ids = [node['id'] for node in res.json['data']]

        assert component._id in ids
        assert component_two._id not in ids


@pytest.mark.django_db
class TestNodeChildCreate:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/children/'.format(API_BASE, project._id)

    @pytest.fixture()
    def child(self):
        return {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project'
                }
            }
        }

    def test_creates_child(self, app, user, project, child, url):

    #   test_creates_child_logged_out_user
        res = app.post_json_api(url, child, expect_errors=True)
        assert res.status_code == 401

        project.reload()
        assert len(project.nodes) == 0

    #   test_creates_child_logged_in_read_contributor
        read_contrib = AuthUserFactory()
        project.add_contributor(read_contrib, permissions=[permissions.READ], auth=Auth(user), save=True)
        res = app.post_json_api(url, child, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        project.reload()
        assert len(project.nodes) == 0

    #   test_creates_child_logged_in_non_contributor
        non_contrib = AuthUserFactory()
        res = app.post_json_api(url, child, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        project.reload()
        assert len(project.nodes) == 0

    #   test_creates_child_no_type
        child = {
            'data': {
                'attributes': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
                }
            }
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_creates_child_incorrect_type
        child = {
            'data': {
                'type': 'Wrong type.',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project',
                }
            }
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

    #   test_creates_child_properties_not_nested
        child = {
            'data': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
            }
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/attributes.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

    def test_creates_child_logged_in_write_contributor(self, app, user, project, child, url):
        write_contrib = AuthUserFactory()
        project.add_contributor(write_contrib, permissions=[permissions.READ, permissions.WRITE], auth=Auth(user), save=True)

        res = app.post_json_api(url, child, auth=write_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['title'] == child['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == child['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == child['data']['attributes']['category']

        project.reload()
        child_id = res.json['data']['id']
        assert child_id == project.nodes[0]._id
        assert AbstractNode.load(child_id).logs.latest().action == NodeLog.PROJECT_CREATED

    def test_creates_child_logged_in_owner(self, app, user, project, child, url):
        res = app.post_json_api(url, child, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['title'] == child['data']['attributes']['title']
        assert res.json['data']['attributes']['description'] == child['data']['attributes']['description']
        assert res.json['data']['attributes']['category'] == child['data']['attributes']['category']

        project.reload()
        assert res.json['data']['id'] == project.nodes[0]._id
        assert project.nodes[0].logs.latest().action == NodeLog.PROJECT_CREATED

    def test_creates_child_creates_child_and_sanitizes_html_logged_in_owner(self, app, user, project, url):
        title = '<em>Reasonable</em> <strong>Project</strong>'
        description = 'An <script>alert("even reasonabler")</script> child'

        res = app.post_json_api(url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': 'project',
                    'public': True
                }
            }
        }, auth=user.auth)
        child_id = res.json['data']['id']
        assert res.status_code == 201
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = app.get(url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == strip_html(title)
        assert res.json['data']['attributes']['description'] == strip_html(description)
        assert res.json['data']['attributes']['category'] == 'project'

        project.reload()
        child_id = res.json['data']['id']
        assert child_id == project.nodes[0]._id
        assert AbstractNode.load(child_id).logs.latest().action == NodeLog.PROJECT_CREATED

    def test_cannot_create_child_on_a_registration(self, app, user, project):
        registration = RegistrationFactory(project=project, creator=user)
        url = '/{}nodes/{}/children/'.format(API_BASE, registration._id)
        res = app.post_json_api(url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'project',
                    'public': True,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestNodeChildrenBulkCreate:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/children/'.format(API_BASE, project._id)

    @pytest.fixture()
    def child_one(self):
        return {
            'type': 'nodes',
            'attributes': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project'
            }
        }

    @pytest.fixture()
    def child_two(self):
        return {
            'type': 'nodes',
            'attributes': {
                'title': 'second child',
                'description': 'this is my hypothesis',
                'category': 'hypothesis'
            }
        }

    def test_bulk_children_create_blank_request(self, app, user, url):
        res = app.post_json_api(url, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400

    def test_bulk_creates_children_limits(self, app, user, child_one, url):
        res = app.post_json_api(url, {'data': [child_one] * 101}, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Bulk operation limit is 100, got 101.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

    def test_bulk_creates_children_auth_errors(self, app, user, project, child_one, child_two, url):

    #   test_bulk_creates_children_logged_out_user
        res = app.post_json_api(url, {'data': [child_one, child_two]}, expect_errors=True, bulk=True)
        assert res.status_code == 401

        project.reload()
        assert len(project.nodes) == 0

    #   test_bulk_creates_children_logged_in_read_contributor
        read_contrib = AuthUserFactory()
        project.add_contributor(read_contrib, permissions=[permissions.READ], auth=Auth(user), save=True)
        res = app.post_json_api(url, {'data': [child_one, child_two]}, auth=read_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 403

        project.reload()
        assert len(project.nodes) == 0

    #   test_bulk_creates_children_logged_in_non_contributor
        non_contrib = AuthUserFactory()
        res = app.post_json_api(url, {'data': [child_one, child_two]}, auth=non_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 403

        project.reload()
        assert len(project.nodes) == 0

    def test_bulk_creates_children_logged_in_owner(self, app, user, project, child_one, child_two, url):
        res = app.post_json_api(url, {'data': [child_one, child_two]}, auth=user.auth, bulk=True)
        assert res.status_code == 201
        assert res.json['data'][0]['attributes']['title'] == child_one['attributes']['title']
        assert res.json['data'][0]['attributes']['description'] == child_one['attributes']['description']
        assert res.json['data'][0]['attributes']['category'] == child_one['attributes']['category']
        assert res.json['data'][1]['attributes']['title'] == child_two['attributes']['title']
        assert res.json['data'][1]['attributes']['description'] == child_two['attributes']['description']
        assert res.json['data'][1]['attributes']['category'] == child_two['attributes']['category']

        project.reload()
        nodes = project.nodes
        assert res.json['data'][0]['id'] == nodes[0]._id
        assert res.json['data'][1]['id'] == nodes[1]._id

        assert nodes[0].logs.latest().action == NodeLog.PROJECT_CREATED
        assert nodes[1].logs.latest().action == NodeLog.PROJECT_CREATED


    def test_bulk_creates_children_child_logged_in_write_contributor(self, app, user, project, child_one, child_two, url):
        write_contrib = AuthUserFactory()
        project.add_contributor(write_contrib, permissions=[permissions.READ, permissions.WRITE], auth=Auth(user), save=True)

        res = app.post_json_api(url, {'data': [child_one, child_two]}, auth=write_contrib.auth, bulk=True)
        assert res.status_code == 201
        assert res.json['data'][0]['attributes']['title'] == child_one['attributes']['title']
        assert res.json['data'][0]['attributes']['description'] == child_one['attributes']['description']
        assert res.json['data'][0]['attributes']['category'] == child_one['attributes']['category']
        assert res.json['data'][1]['attributes']['title'] == child_two['attributes']['title']
        assert res.json['data'][1]['attributes']['description'] == child_two['attributes']['description']
        assert res.json['data'][1]['attributes']['category'] == child_two['attributes']['category']

        project.reload()
        child_id = res.json['data'][0]['id']
        child_two_id = res.json['data'][1]['id']
        nodes = project.nodes
        assert child_id == nodes[0]._id
        assert child_two_id == nodes[1]._id

        assert AbstractNode.load(child_id).logs.latest().action == NodeLog.PROJECT_CREATED
        assert nodes[1].logs.latest().action == NodeLog.PROJECT_CREATED

    def test_bulk_creates_children_and_sanitizes_html_logged_in_owner(self, app, user, project, url):
        title = '<em>Reasoning</em> <strong>Aboot Projects</strong>'
        description = 'A <script>alert("super reasonable")</script> child'

        res = app.post_json_api(url, {
            'data': [{
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': 'project',
                    'public': True
                }
            }]
        }, auth=user.auth, bulk=True)
        child_id = res.json['data'][0]['id']
        assert res.status_code == 201
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = app.get(url, auth=user.auth)
        assert res.json['data']['attributes']['title'] == strip_html(title)
        assert res.json['data']['attributes']['description'] == strip_html(description)
        assert res.json['data']['attributes']['category'] == 'project'

        project.reload()
        child_id = res.json['data']['id']
        assert child_id == project.nodes[0]._id
        assert AbstractNode.load(child_id).logs.latest().action == NodeLog.PROJECT_CREATED

    def test_cannot_bulk_create_children_on_a_registration(self, app, user, project, child_two):
        registration = RegistrationFactory(project=project, creator=user)
        url = '/{}nodes/{}/children/'.format(API_BASE, registration._id)
        res = app.post_json_api(url, {
            'data': [child_two, {
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'project',
                    'public': True,
                }
            }]
        }, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 404

        project.reload()
        assert len(project.nodes) == 0

    def test_bulk_creates_children_payload_errors(self, app, user, project, child_two, url):

    # def test_bulk_creates_children_no_type(self, app, user, project, child_two, url):
        child = {
            'data': [child_two, {
                'attributes': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
                }
            }]
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/1/type'

        project.reload()
        assert len(project.nodes) == 0

    # def test_bulk_creates_children_incorrect_type(self, app, user, project, child_two, url):
        child = {
            'data': [child_two, {
                'type': 'Wrong type.',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project',
                }
            }]
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.'

        project.reload()
        assert len(project.nodes) == 0

    # def test_bulk_creates_children_properties_not_nested(self, app, user, project, child_two, url):
        child = {
            'data': [child_two, {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
            }]
        }
        res = app.post_json_api(url, child, auth=user.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/attributes.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes'

        project.reload()
        assert len(project.nodes) == 0

