# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.models import Node, NodeLog
from website.util import permissions
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)


class TestNodeChildrenList(ApiTestCase):
    def setUp(self):
        super(TestNodeChildrenList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory()
        self.project.add_contributor(self.user, permissions=[permissions.READ, permissions.WRITE])
        self.project.save()
        self.component = NodeFactory(parent=self.project, creator=self.user)
        self.pointer = ProjectFactory()
        self.project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_project_url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.save()
        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_project_url = '/{}nodes/{}/children/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_node_children_list_does_not_include_pointers(self):
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_return_public_node_children_list_logged_out(self):
        res = self.app.get(self.public_project_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_public_node_children_list_logged_in(self):
        res = self.app.get(self.public_project_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_private_node_children_list_logged_out(self):
        res = self.app.get(self.private_project_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_node_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.component._id)

    def test_return_private_node_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_node_children_list_does_not_include_unauthorized_projects(self):
        private_component = NodeFactory(parent=self.project)
        res = self.app.get(self.private_project_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_node_children_list_does_not_include_deleted(self):
        child_project = NodeFactory(parent=self.public_project, creator=self.user)
        child_project.save()

        res = self.app.get(self.public_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        ids = [node['id'] for node in res.json['data']]
        assert_in(child_project._id, ids)
        assert_equal(2, len(ids))

        child_project.is_deleted = True
        child_project.save()

        res = self.app.get(self.public_project_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        ids = [node['id'] for node in res.json['data']]
        assert_not_in(child_project._id, ids)
        assert_equal(1, len(ids))

    def test_node_children_list_does_not_include_node_links(self):
        pointed_to = ProjectFactory(is_public=True)

        self.public_project.add_pointer(pointed_to, auth=Auth(self.public_project.creator))

        res = self.app.get(self.public_project_url, auth=self.user.auth)
        ids = [node['id'] for node in res.json['data']]
        assert_in(self.public_component._id, ids)  # sanity check

        assert_equal(len(ids), len([e for e in self.public_project.nodes if e.primary]))
        assert_not_in(pointed_to._id, ids)


class TestNodeChildrenListFiltering(ApiTestCase):

    def test_node_child_filtering(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)

        title1, title2 = fake.bs(), fake.bs()
        component = NodeFactory(title=title1, parent=project)
        component2 = NodeFactory(title=title2, parent=project)

        url = '/{}nodes/{}/children/?filter[title]={}'.format(
            API_BASE,
            project._id,
            title1
        )
        res = self.app.get(url, auth=user.auth)

        ids = [node['id'] for node in res.json['data']]

        assert_in(component._id, ids)
        assert_not_in(component2._id, ids)


class TestNodeChildCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeChildCreate, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_public=True)

        self.url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)
        self.child = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project'
                }
            }
        }

    def test_creates_child_logged_out_user(self):
        res = self.app.post_json_api(self.url, self.child, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_logged_in_owner(self):
        res = self.app.post_json_api(self.url, self.child, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['data']['attributes']['category'])

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)
        assert_equal(self.project.nodes[0].logs[0].action, NodeLog.PROJECT_CREATED)

    def test_creates_child_logged_in_write_contributor(self):
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user), save=True)

        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['data']['attributes']['category'])

        self.project.reload()
        child_id = res.json['data']['id']
        assert_equal(child_id, self.project.nodes[0]._id)
        assert_equal(Node.load(child_id).logs[0].action, NodeLog.PROJECT_CREATED)

    def test_creates_child_logged_in_read_contributor(self):
        self.project.add_contributor(self.user_two, permissions=[permissions.READ], auth=Auth(self.user), save=True)
        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_creates_child_and_sanitizes_html_logged_in_owner(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> child'

        res = self.app.post_json_api(self.url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': 'project',
                    'public': True
                }
            }
        }, auth=self.user.auth)
        child_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], 'project')

        self.project.reload()
        child_id = res.json['data']['id']
        assert_equal(child_id, self.project.nodes[0]._id)
        assert_equal(Node.load(child_id).logs[0].action, NodeLog.PROJECT_CREATED)

    def test_cannot_create_child_on_a_registration(self):
        registration = RegistrationFactory(project=self.project, creator=self.user)
        url = '/{}nodes/{}/children/'.format(API_BASE, registration._id)
        res = self.app.post_json_api(url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'project',
                    'public': True,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_creates_child_no_type(self):
        child = {
            'data': {
                'attributes': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
                }
            }
        }
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_creates_child_incorrect_type(self):
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
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.')

    def test_creates_child_properties_not_nested(self):
        child = {
            'data': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
            }
        }
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/attributes.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')


class TestNodeChildrenBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeChildrenBulkCreate, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_public=True)

        self.url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)
        self.child = {
                'type': 'nodes',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project'
                }
        }
        self.child_two = {
                'type': 'nodes',
                'attributes': {
                    'title': 'second child',
                    'description': 'this is my hypothesis',
                    'category': 'hypothesis'
                }
        }

    def test_bulk_children_create_blank_request(self):
        res = self.app.post_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_creates_children_limits(self):
        res = self.app.post_json_api(self.url, {'data': [self.child] * 101},
                                     auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 100, got 101.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_creates_children_logged_out_user(self):
        res = self.app.post_json_api(self.url, {'data': [self.child, self.child_two]}, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_logged_in_owner(self):
        res = self.app.post_json_api(self.url, {'data': [self.child, self.child_two]}, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data'][0]['attributes']['title'], self.child['attributes']['title'])
        assert_equal(res.json['data'][0]['attributes']['description'], self.child['attributes']['description'])
        assert_equal(res.json['data'][0]['attributes']['category'], self.child['attributes']['category'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.child_two['attributes']['title'])
        assert_equal(res.json['data'][1]['attributes']['description'], self.child_two['attributes']['description'])
        assert_equal(res.json['data'][1]['attributes']['category'], self.child_two['attributes']['category'])

        self.project.reload()
        assert_equal(res.json['data'][0]['id'], self.project.nodes[0]._id)
        assert_equal(res.json['data'][1]['id'], self.project.nodes[1]._id)

        assert_equal(self.project.nodes[0].logs[0].action, NodeLog.PROJECT_CREATED)
        assert_equal(self.project.nodes[1].logs[0].action, NodeLog.PROJECT_CREATED)


    def test_bulk_creates_children_child_logged_in_write_contributor(self):
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user), save=True)

        res = self.app.post_json_api(self.url, {'data': [self.child, self.child_two]}, auth=self.user_two.auth, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data'][0]['attributes']['title'], self.child['attributes']['title'])
        assert_equal(res.json['data'][0]['attributes']['description'], self.child['attributes']['description'])
        assert_equal(res.json['data'][0]['attributes']['category'], self.child['attributes']['category'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.child_two['attributes']['title'])
        assert_equal(res.json['data'][1]['attributes']['description'], self.child_two['attributes']['description'])
        assert_equal(res.json['data'][1]['attributes']['category'], self.child_two['attributes']['category'])

        self.project.reload()
        child_id = res.json['data'][0]['id']
        child_two_id = res.json['data'][1]['id']
        assert_equal(child_id, self.project.nodes[0]._id)
        assert_equal(child_two_id, self.project.nodes[1]._id)

        assert_equal(Node.load(child_id).logs[0].action, NodeLog.PROJECT_CREATED)
        assert_equal(self.project.nodes[1].logs[0].action, NodeLog.PROJECT_CREATED)

    def test_bulk_creates_children_logged_in_read_contributor(self):
        self.project.add_contributor(self.user_two, permissions=[permissions.READ], auth=Auth(self.user), save=True)
        res = self.app.post_json_api(self.url, {'data': [self.child, self.child_two]}, auth=self.user_two.auth,
                                     expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.url, {'data': [self.child, self.child_two]},
                                     auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_and_sanitizes_html_logged_in_owner(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> child'

        res = self.app.post_json_api(self.url, {
            'data': [{
                'type': 'nodes',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': 'project',
                    'public': True
                }
            }]
        }, auth=self.user.auth, bulk=True)
        child_id = res.json['data'][0]['id']
        assert_equal(res.status_code, 201)
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], 'project')

        self.project.reload()
        child_id = res.json['data']['id']
        assert_equal(child_id, self.project.nodes[0]._id)
        assert_equal(Node.load(child_id).logs[0].action, NodeLog.PROJECT_CREATED)

    def test_cannot_bulk_create_children_on_a_registration(self):
        registration = RegistrationFactory(project=self.project, creator=self.user)
        url = '/{}nodes/{}/children/'.format(API_BASE, registration._id)
        res = self.app.post_json_api(url, {
            'data': [self.child_two, {
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'project',
                    'public': True,
                }
            }]
        }, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 404)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_no_type(self):
        child = {
            'data': [self.child_two, {
                'attributes': {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
                }
            }]
        }
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/type')

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_incorrect_type(self):
        child = {
            'data': [self.child_two, {
                'type': 'Wrong type.',
                'attributes': {
                    'title': 'child',
                    'description': 'this is a child project',
                    'category': 'project',
                }
            }]
        }
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'This resource has a type of "nodes", but you set the json body\'s type field to "Wrong type.". You probably need to change the type field to match the resource\'s type.')

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_bulk_creates_children_properties_not_nested(self):
        child = {
            'data': [self.child_two, {
                'title': 'child',
                'description': 'this is a child project',
                'category': 'project',
            }]
        }
        res = self.app.post_json_api(self.url, child, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/attributes.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)
