# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.models import Node, NodeLog
from website.util import permissions
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    DashboardFactory,
    FolderFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    RetractedRegistrationFactory
)


class TestNodeList(ApiTestCase):
    def setUp(self):
        super(TestNodeList, self).setUp()
        self.user = AuthUserFactory()

        self.non_contrib = AuthUserFactory()

        self.deleted = ProjectFactory(is_deleted=True)
        self.private = ProjectFactory(is_public=False, creator=self.user)
        self.public = ProjectFactory(is_public=True, creator=self.user)

        self.url = '/{}nodes/'.format(API_BASE)

    def tearDown(self):
        super(TestNodeList, self).tearDown()
        Node.remove()

    def test_only_returns_non_deleted_public_projects(self):
        res = self.app.get(self.url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public._id, ids)
        assert_not_in(self.deleted._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_out_user(self):
        res = self.app.get(self.url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_node_list_logged_in_user(self):
        res = self.app.get(self.url, auth=self.non_contrib)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_out_user(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_node_list_returns_registrations(self):
        registration = RegistrationFactory(project=self.public, creator=self.user)
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(registration._id, ids)

    def test_omit_retracted_registration(self):
        registration = RegistrationFactory(creator=self.user, project=self.public)
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 3)
        retraction = RetractedRegistrationFactory(registration=registration, user=registration.creator)
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)


class TestNodeFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeFiltering, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True)
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

        self.url = "/{}nodes/".format(API_BASE)

    def tearDown(self):
        super(TestNodeFiltering, self).tearDown()
        Node.remove()

    def test_filtering_by_category(self):
        project = ProjectFactory(creator=self.user_one, category='hypothesis')
        project2 = ProjectFactory(creator=self.user_one, category='procedure')
        url = '/{}nodes/?filter[category]=hypothesis'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)

        node_json = res.json['data']
        ids = [each['id'] for each in node_json]

        assert_in(project._id, ids)
        assert_not_in(project2._id, ids)

    def test_filtering_by_public(self):
        project = ProjectFactory(creator=self.user_one, is_public=True)
        project2 = ProjectFactory(creator=self.user_one, is_public=False)

        url = '/{}nodes/?filter[public]=false'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        # No public projects returned
        assert_false(
            any([each['attributes']['public'] for each in node_json])
        )

        ids = [each['id'] for each in node_json]
        assert_not_in(project._id, ids)
        assert_in(project2._id, ids)

        url = '/{}nodes/?filter[public]=true'.format(API_BASE)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        # No private projects returned
        assert_true(
            all([each['attributes']['public'] for each in node_json])
        )

        ids = [each['id'] for each in node_json]
        assert_not_in(project2._id, ids)
        assert_in(project._id, ids)

    def test_filtering_tags(self):
        tag1, tag2 = 'tag1', 'tag2'
        self.project_one.add_tag(tag1, Auth(self.project_one.creator), save=False)
        self.project_one.add_tag(tag2, Auth(self.project_one.creator), save=False)
        self.project_one.save()

        self.project_two.add_tag(tag1, Auth(self.project_two.creator), save=True)

        # both project_one and project_two have tag1
        url = '/{}nodes/?filter[tags]={}'.format(API_BASE, tag1)

        res = self.app.get(url, auth=self.project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)

        # filtering two tags
        # project_one has both tags; project_two only has one
        url = '/{}nodes/?filter[tags]={}&filter[tags]={}'.format(API_BASE, tag1, tag2)

        res = self.app.get(url, auth=self.project_one.creator.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)

    def test_get_all_projects_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_all_projects_with_no_filter_not_logged_in(self):
        res = self.app.get(self.url)
        node_json = res.json['data']
        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_one_project_with_exact_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project%20One".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_not_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_some_projects_with_substring_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Two".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_or_my_projects_with_filter_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_get_only_public_projects_with_filter_not_logged_in(self):
        url = "/{}nodes/?filter[title]=Project".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_alternate_filtering_field_not_logged_in(self):
        url = "/{}nodes/?filter[description]=Three".format(API_BASE)

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_not_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        url = '/{}nodes/?filter[notafield]=bogus'.format(API_BASE)

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], "'notafield' is not a valid field for this endpoint.")


class TestNodeCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {
            'data': {
                'type': 'nodes',
                'attributes':
                    {
                        'title': self.title,
                        'description': self.description,
                        'category': self.category,
                        'public': True,
                    }
            }
        }
        self.private_project = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
            }
        }
    def test_node_create_invalid_data(self):
        res = self.app.post_json_api(self.url, "Incorrect data", auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

        res = self.app.post_json_api(self.url, ["Incorrect data"], auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_creates_public_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_public_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.public_project['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.public_project['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.public_project['data']['attributes']['category'])
        assert_equal(res.content_type, 'application/vnd.api+json')
        pid = res.json['data']['id']
        project = Node.load(pid)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

    def test_creates_private_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.private_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_private_project_logged_in_contributor(self):
        res = self.app.post_json_api(self.url, self.private_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project['data']['attributes']['title'])
        assert_equal(res.json['data']['attributes']['description'], self.private_project['data']['attributes']['description'])
        assert_equal(res.json['data']['attributes']['category'], self.private_project['data']['attributes']['category'])
        pid = res.json['data']['id']
        project = Node.load(pid)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

    def test_creates_project_creates_project_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> project'

        res = self.app.post_json_api(self.url, {
            'data': {
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': self.category,
                    'public': True
                },
                'type': 'nodes'
            }
        }, auth=self.user_one.auth)
        project_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = '/{}nodes/{}/'.format(API_BASE, project_id)

        project = Node.load(project_id)
        assert_equal(project.logs[-1].action, NodeLog.PROJECT_CREATED)

        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_creates_project_no_type(self):
        project = {
            'data': {
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_creates_project_incorrect_type(self):
        project = {
            'data': {
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                },
                'type': 'Wrong type.'
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

    def test_creates_project_properties_not_nested(self):
        project = {
            'data': {
                'title': self.title,
                'description': self.description,
                'category': self.category,
                'public': False,
                'type': 'nodes'
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/attributes.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

    def test_create_project_invalid_title(self):
        project = {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': 'A' * 201,
                    'description': self.description,
                    'category': self.category,
                    'public': False,
                }
            }
        }
        res = self.app.post_json_api(self.url, project, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')


class TestNodeBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': True
                }
        }

        self.private_project = {
                'type': 'nodes',
                'attributes': {
                    'title': self.title,
                    'description': self.description,
                    'category': self.category,
                    'public': False
                }
        }

        self.empty_project = {'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}}

    def test_bulk_create_nodes_blank_request(self):
        res = self.app.post_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_create_all_or_nothing(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.empty_project]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_out(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.private_project]}, bulk=True, expect_errors=True)
        assert_equal(res.status_code, 401)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_error_formatting(self):
        res = self.app.post_json_api(self.url, {'data': [self.empty_project, self.empty_project]}, bulk=True, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ["This field may not be blank.", "This field may not be blank."])

    def test_bulk_create_limits(self):
        node_create_list = {'data': [self.public_project] * 11}
        res = self.app.post_json_api(self.url, node_create_list, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_type(self):
        payload = {'data': [{"attributes": {'category': self.category, 'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/0/type')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_incorrect_type(self):
        payload = {'data': [self.public_project, {'type': 'Incorrect type.', "attributes": {'category': self.category, 'title': self.title}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_attributes(self):
        payload = {'data': [self.public_project, {'type': 'nodes', }]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_no_title(self):
        payload = {'data': [self.public_project, {'type': 'nodes', "attributes": {'category': self.category}}]}
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/attributes/title')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_ugly_payload(self):
        payload = 'sdf;jlasfd'
        res = self.app.post_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_in(self):
        res = self.app.post_json_api(self.url, {'data': [self.public_project, self.private_project]}, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['attributes']['title'], self.public_project['attributes']['title'])
        assert_equal(res.json['data'][0]['attributes']['category'], self.public_project['attributes']['category'])
        assert_equal(res.json['data'][0]['attributes']['description'], self.public_project['attributes']['description'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.private_project['attributes']['title'])
        assert_equal(res.json['data'][1]['attributes']['category'], self.public_project['attributes']['category'])
        assert_equal(res.json['data'][1]['attributes']['description'], self.public_project['attributes']['description'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 2)
        id_one = res.json['data'][0]['id']
        id_two = res.json['data'][1]['id']

        res = self.app.delete_json_api(self.url, {'data': [{'id': id_one, 'type': 'nodes'},
                                                           {'id': id_two, 'type': 'nodes'}]},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 204)


class TestNodeBulkUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'

        self.new_category = 'project'

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_project_two = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user)

        self.public_payload = {
            'data': [
                {
                    'id': self.public_project._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                },
                {
                    'id': self.public_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': True
                    }
                }
            ]
        }

        self.url = '/{}nodes/'.format(API_BASE)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_project_two = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_payload = {'data': [
                {
                    'id': self.private_project._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': False
                    }
                },
                {
                    'id': self.private_project_two._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                        'description': self.new_description,
                        'category': self.new_category,
                        'public': False
                    }
                }
            ]
        }


        self.empty_payload = {'data': [
            {'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}},
            {'id': self.public_project_two._id, 'type': 'nodes', 'attributes': {'title': "", 'description': "", "category": ""}}
        ]}

    def test_bulk_update_nodes_blank_request(self):
        res = self.app.put_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_update_blank_but_not_empty_title(self):
        payload = {
            "data": [
                {
                  "id": self.public_project._id,
                  "type": "nodes",
                  "attributes": {
                    "title": "This shouldn't update.",
                    "category": "instrumentation"
                  }
                },
                {
                  "id": self.public_project_two._id,
                  "type": "nodes",
                  "attributes": {
                    "title": " ",
                    "category": "hypothesis"
                  }
                }
              ]
            }
        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.put_json_api(self.url, payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_with_tags(self):
        new_payload = {'data': [{'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': 'New title', 'category': 'project', 'tags': ['new tag']}}]}

        res = self.app.put_json_api(self.url, new_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['tags'], ['new tag'])

    def test_bulk_update_public_projects_one_not_found(self):
        empty_payload = {'data': [
            {
                'id': 12345,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'category': self.new_category
                }
            }, self.public_payload['data'][0]
        ]}

        res = self.app.put_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')


        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)


    def test_bulk_update_public_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_public_projects_logged_in(self):
        res = self.app.put_json_api(self.url, self.public_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_update_private_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_private_projects_logged_in_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_update_private_projects_logged_in_non_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        self.private_project_two.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_projects_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.url, {'data': {'id': self.public_project._id, 'type': 'nodes',
                                                        'attributes': {'title': self.new_title, 'category': "project"}}},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_update_error_formatting(self):
        res = self.app.put_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.'] * 2)

    def test_bulk_update_id_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'type': 'nodes', 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/id')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_type_not_supplied(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'id': self.public_project._id, 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/1/type')
        assert_equal(res.json['errors'][0]['detail'], "This field may not be null.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_incorrect_type(self):
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], {'id': self.public_project._id, 'type': 'Incorrect', 'attributes':
            {'title': self.new_title, 'category': self.new_category}}]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_limits(self):
        node_update_list = {'data': [self.public_payload['data'][0]] * 11}
        res = self.app.put_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_update_no_title_or_category(self):
        new_payload = {'id': self.public_project._id, 'type': 'nodes', 'attributes': {}}
        res = self.app.put_json_api(self.url, {'data': [self.public_payload['data'][1], new_payload]}, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)


class TestNodeBulkPartialUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkPartialUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'

        self.new_category = 'project'

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_project_two = ProjectFactory(title=self.title,
                                                description=self.description,
                                                category=self.category,
                                                is_public=True,
                                                creator=self.user)

        self.public_payload = {'data': [
            {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            {
                'id': self.public_project_two._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        ]}

        self.url = '/{}nodes/'.format(API_BASE)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_project_two = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)

        self.private_payload = {'data': [
            {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            {
                'id': self.private_project_two._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        ]}

        self.empty_payload = {'data': [
            {'id': self.public_project._id, 'type': 'nodes', 'attributes': {'title': ""}},
            {'id': self.public_project_two._id, 'type': 'nodes', 'attributes': {'title': ""}}
        ]
        }

    def test_bulk_patch_nodes_blank_request(self):
        res = self.app.patch_json_api(self.url, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_partial_update_public_projects_one_not_found(self):
        empty_payload = {'data': [
            {
                'id': 12345,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            },
            self.public_payload['data'][0]
        ]}
        res = self.app.patch_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to update.')

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_public_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_public_projects_logged_in(self):
        res = self.app.patch_json_api(self.url, self.public_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_partial_update_private_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_private_projects_logged_in_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user.auth, bulk=True)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_bulk_partial_update_private_projects_logged_in_non_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        self.private_project_two.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_projects_send_dictionary_not_list(self):
        res = self.app.patch_json_api(self.url, {'data': {'id': self.public_project._id, 'attributes': {'title': self.new_title, 'category': "project"}}},
                                    auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_partial_update_error_formatting(self):
        res = self.app.patch_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/0/attributes/title'}, {'pointer': '/data/1/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.']*2)

    def test_bulk_partial_update_id_not_supplied(self):
        res = self.app.patch_json_api(self.url, {'data': [{'type': 'nodes', 'attributes': {'title': self.new_title}}]},
                                      auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')

    def test_bulk_partial_update_limits(self):
        node_update_list = {'data': [self.public_payload['data'][0]] * 11 }
        res = self.app.patch_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True, bulk=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')


class TestNodeBulkDelete(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkDelete, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project_one = ProjectFactory(title="Project One", is_public=True, creator=self.user_one, category="project")
        self.project_two = ProjectFactory(title="Project Two", description="One Three", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One",
                                                       is_public=False,
                                                       creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two",
                                                       is_public=False,
                                                       creator=self.user_two)

        self.url = "/{}nodes/".format(API_BASE)
        self.project_one_url = '/{}nodes/{}/'.format(API_BASE, self.project_one._id)
        self.project_two_url = '/{}nodes/{}/'.format(API_BASE, self.project_two._id)
        self.private_project_url = "/{}nodes/{}/".format(API_BASE, self.private_project_user_one._id)

        self.public_payload = {'data': [{'id': self.project_one._id, 'type': 'nodes'}, {'id': self.project_two._id, 'type': 'nodes'}]}
        self.private_payload = {'data': [{'id': self.private_project_user_one._id, 'type': 'nodes'}]}

    def test_bulk_delete_nodes_blank_request(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)

    def test_bulk_delete_no_type(self):
        payload = {'data': [
            {'id': self.project_one._id},
            {'id': self.project_two._id}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')

    def test_bulk_delete_no_id(self):
        payload = {'data': [
            {'type': 'nodes'},
            {'id': 'nodes'}
        ]}
        res = self.app.delete_json_api(self.url, payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/id.')

    def test_bulk_delete_dict_inside_data(self):
        res = self.app.delete_json_api(self.url, {'data': {'id': self.project_one._id, 'type': 'nodes'}},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_delete_invalid_type(self):
        res = self.app.delete_json_api(self.url, {'data': [{'type': 'Wrong type', 'id': self.project_one._id}]},
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 409)

    def test_bulk_delete_public_projects_logged_in(self):
        res = self.app.delete_json_api(self.url, self.public_payload, auth=self.user_one.auth, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.project_one.reload()
        self.project_two.reload()

    def test_bulk_delete_public_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.public_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

        res = self.app.get(self.project_two_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_private_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.private_payload, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_bulk_delete_private_projects_logged_in_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.private_project_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.private_project_user_one.reload()

    def test_bulk_delete_private_projects_logged_in_non_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_private_projects_logged_in_read_only_contributor(self):
        self.private_project_user_one.add_contributor(self.user_two, permissions=[permissions.READ], save=True)
        res = self.app.delete_json_api(self.url, self.private_payload,
                                       auth=self.user_two.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_all_or_nothing(self):
        new_payload = {'data': [{'id': self.private_project_user_one._id, 'type': 'nodes'}, {'id': self.private_project_user_two._id, 'type': 'nodes'}]}
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

        url = "/{}nodes/{}/".format(API_BASE, self.private_project_user_two._id)
        res = self.app.get(url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_limits(self):
        new_payload = {'data': [{'id': self.private_project_user_one._id, 'type':'nodes'}] * 11 }
        res = self.app.delete_json_api(self.url, new_payload,
                                       auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_bulk_delete_invalid_payload_one_not_found(self):
        new_payload = {'data': [self.public_payload['data'][0], {'id': '12345', 'type': 'nodes'}]}
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Could not find all objects to delete.')

        res = self.app.get(self.project_one_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_no_payload(self):
        res = self.app.delete_json_api(self.url, auth=self.user_one.auth, expect_errors=True, bulk=True)
        assert_equal(res.status_code, 400)
