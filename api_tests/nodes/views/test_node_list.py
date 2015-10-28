# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.models import Node, NodeLog
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    DashboardFactory,
    FolderFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory
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

    def test_node_list_does_not_return_registrations(self):
        registration = RegistrationFactory(project=self.public, creator=self.user)
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_not_in(registration._id, ids)


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
