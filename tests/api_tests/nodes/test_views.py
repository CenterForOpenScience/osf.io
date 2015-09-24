# -*- coding: utf-8 -*-
import mock
import base64
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.addons.github import model
from website.models import Node, NodeLog
from website.views import find_dashboard
from website.util import permissions
from website.util.sanitize import strip_html

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from tests.factories import (
    DashboardFactory,
    FolderFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
    AuthUserFactory
)
from tests.utils import assert_logs, assert_not_logs


class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        super(TestWelcomeToApi, self).setUp()
        self.user = AuthUserFactory()
        self.url = '/{}'.format(API_BASE)

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user'], None)

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['meta']['current_user']['data']['attributes']['given_name'], self.user.given_name)


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

    def test_filtering_registrations(self):
        url = '/{}nodes/?filter[registration]=true'.format(API_BASE)
        registration = RegistrationFactory(creator=self.user_one)

        res = self.app.get(url, auth=self.user_one.auth, expect_errors=True)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_not_in(self.project_one._id, ids)
        assert_in(registration._id, ids)

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
        assert_equal(errors[0]['detail'], 'Query string contains an invalid filter.')


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
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
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


class TestNodeDetail(ApiTestCase):
    def setUp(self):
        super(TestNodeDetail, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        self.public_component_url = '/{}nodes/{}/'.format(API_BASE, self.public_component._id)

    def test_return_public_project_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)

    def test_return_public_project_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.public_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.public_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.public_project.category)

    def test_return_private_project_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_private_project_details_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project.title)
        assert_equal(res.json['data']['attributes']['description'], self.private_project.description)
        assert_equal(res.json['data']['attributes']['category'], self.private_project.category)

    def test_return_private_project_details_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_top_level_project_has_no_parent(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['relationships']['parent']['links']['self']['href'], None)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_child_project_has_parent(self):
        public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        public_component_url = '/{}nodes/{}/'.format(API_BASE, public_component._id)
        res = self.app.get(public_component_url)
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['parent']['links']['self']['href']
        assert_equal(urlparse(url).path, self.public_url)

    def test_node_has_children_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['children']['links']['related']['href']
        expected_url = self.public_url + 'children/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_contributors_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['contributors']['links']['related']['href']
        expected_url = self.public_url + 'contributors/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_pointers_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = self.public_url + 'node_links/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_registrations_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['registrations']['links']['related']['href']
        expected_url = self.public_url + 'registrations/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_has_files_link(self):
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['files']['links']['related']['href']
        expected_url = self.public_url + 'files/'
        assert_equal(urlparse(url).path, expected_url)

    def test_node_properties(self):
        res = self.app.get(self.public_url)
        assert_equal(res.json['data']['attributes']['public'], True)
        assert_equal(res.json['data']['attributes']['registration'], False)
        assert_equal(res.json['data']['attributes']['collection'], False)
        assert_equal(res.json['data']['attributes']['dashboard'], False)
        assert_equal(res.json['data']['attributes']['tags'], [])

    def test_requesting_folder_returns_error(self):
        folder = NodeFactory(is_folder=True, creator=self.user)
        res = self.app.get(
            '/{}nodes/{}/'.format(API_BASE, folder._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 404)


class NodeCRUDTestCase(ApiTestCase):

    def setUp(self):
        super(NodeCRUDTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'
        self.description = 'A Properly Cool Project'
        self.new_description = 'An even cooler project'
        self.category = 'data'
        self.new_category = 'project'

        self.public_project = ProjectFactory(title=self.title,
                                             description=self.description,
                                             category=self.category,
                                             is_public=True,
                                             creator=self.user)

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.fake_url = '/{}nodes/{}/'.format(API_BASE, '12345')


class TestNodeUpdate(NodeCRUDTestCase):

    def test_update_project_properties_not_nested(self):
        res = self.app.put_json_api(self.public_url, {
            'id': self.public_project._id,
            'type': 'nodes',
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data')

    def test_update_invalid_id(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_invalid_type(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'node',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_update_no_id(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_update_no_type(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_update_public_project_logged_out(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_update_public_project_logged_in(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_public_project_logged_in_but_unauthorized(self):
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': True
                }
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_cannot_update_a_registration(self):
        registration = RegistrationFactory(project=self.public_project, creator=self.user)
        original_title = registration.title
        original_description = registration.description
        url = '/{}nodes/{}/'.format(API_BASE, registration._id)
        res = self.app.put_json_api(url, {
            'data': {
                'id': registration._id,
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'hypothesis',
                 'public': True
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        registration.reload()
        assert_equal(res.status_code, 403)
        assert_equal(registration.title, original_title)
        assert_equal(registration.description, original_description)

    def test_update_private_project_logged_out(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'private_project')
    def test_update_private_project_logged_in_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_private_project_logged_in_non_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                    'description': self.new_description,
                    'category': self.new_category,
                    'public': False
                }
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_update_project_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        res = self.app.put_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'description': new_description,
                    'category': self.new_category,
                    'public': True,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(new_description))

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        res = self.app.patch_json_api(self.public_url, {
            'data': {
            'id': self.public_project._id,
            'type': 'nodes',
                'attributes': {
                    'title': new_title
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_write_to_public_field_non_contrib_forbidden(self):
        # Test non-contrib writing to public field
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'attributes': {
                    'public': False},
                'id': self.public_project._id,
                'type': 'nodes'
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_not_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_write_to_public_field_does_not_update(self):
        # Test creator writing to public field (supposed to be read-only)
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'public': False,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_true(res.json['data']['attributes']['public'])
        # django returns a 200 on PATCH to read only field, even though it does not update the field.
        assert_equal(res.status_code, 200)

    def test_partial_update_public_project_logged_out(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'public_project')
    def test_partial_update_public_project_logged_in(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                'title': self.new_title,
                }
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_public_project_logged_in_but_unauthorized(self):
        # Public resource, logged in, unauthorized
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.public_project._id,
                'type': 'nodes',
            }
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_partial_update_private_project_logged_out(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title
                }
            }
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.UPDATED_FIELDS, 'private_project')
    def test_partial_update_private_project_logged_in_contributor(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.private_project._id,
                'type': 'nodes',
            }
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_private_project_logged_in_non_contributor(self):
        res = self.app.patch_json_api(self.private_url, {
            'data': {
                'attributes': {
                    'title': self.new_title},
                'id': self.private_project._id,
                'type': 'nodes',
            }
        }, auth=self.user_two.auth,expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_partial_update_invalid_id(self):
        res = self.app.patch_json_api(self.public_url, {
                'data': {
                    'id': '12345',
                    'type': 'nodes',
                    'attributes': {
                        'title': self.new_title,
                    }
                }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_invalid_type(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'node',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_partial_update_no_id(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')

    def test_partial_update_no_type(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'attributes': {
                    'title': self.new_title,
                }
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    # Nothing will be updated here
    def test_partial_update_project_properties_not_nested(self):
        res = self.app.patch_json_api(self.public_url, {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'title': self.new_title,
            }
        }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_update_project_invalid_title(self):
        project = {
            'data': {
                'type': 'nodes',
                'id': self.public_project._id,
                'attributes': {
                    'title': 'A' * 201,
                    'category': 'project',
                }
            }
        }
        res = self.app.put_json_api(self.public_url, project, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Title cannot exceed 200 characters.')


class TestNodeDelete(NodeCRUDTestCase):

    def test_deletes_public_node_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_public_node_fails_if_unauthorized(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.public_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.PROJECT_DELETED, 'public_project')
    def test_deletes_public_node_succeeds_as_owner(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.public_project.is_deleted, True)

    def test_deletes_private_node_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    @assert_logs(NodeLog.PROJECT_DELETED, 'private_project')
    def test_deletes_private_node_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.private_project.is_deleted, True)

    def test_deletes_private_node_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.private_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_read_only_contributor(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ])
        self.private_project.save()
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.private_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.private_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_invalid_node(self):
        res = self.app.delete(self.fake_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_delete_project_with_component_returns_error(self):
        project = ProjectFactory(creator=self.user)
        component = NodeFactory(parent=project, creator=self.user)
        # Return a 400 because component must be deleted before deleting the parent
        res = self.app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, project._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(
            errors[0]['detail'],
            'Any child components must be deleted prior to deleting this project.'
        )

    def test_delete_dashboard_returns_error(self):
        dashboard_node = find_dashboard(self.user)
        res = self.app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, dashboard_node._id),
            auth=self.user.auth,
            expect_errors=True
        )
        # Dashboards are a folder, so a 404 is returned
        assert_equal(res.status_code, 404)


class TestNodeContributorList(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorList, self).setUp()
        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    def test_return_public_contributor_list_logged_out(self):
        self.public_project.add_contributor(self.user_two, save=True)

        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_public_contributor_list_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.user._id)

    def test_return_private_contributor_list_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_contributor_list_logged_in_contributor(self):
        self.private_project.add_contributor(self.user_two)
        self.private_project.save()

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['id'], self.user._id)
        assert_equal(res.json['data'][1]['id'], self.user_two._id)

    def test_return_private_contributor_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestNodeContributorFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeContributorFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_filtering_node_with_only_bibliographic_contributors(self):

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)
        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_node_with_non_bibliographic_contributor(self):
        non_bibliographic_contrib = UserFactory()
        self.project.add_contributor(non_bibliographic_contrib, visible=False)
        self.project.save()

        base_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.project._id)

        # no filter
        res = self.app.get(base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

        # filter for bibliographic contributors
        url = base_url + '?filter[bibliographic]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes'].get('bibliographic', None))

        # filter for non-bibliographic contributors
        url = base_url + '?filter[bibliographic]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0]['attributes'].get('bibliographic', None))

    def test_filtering_on_invalid_field(self):
        url = '/{}nodes/{}/contributors/?filter[invalid]=foo'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Query string contains an invalid filter.')


class TestNodeContributorAdd(NodeCRUDTestCase):

    def setUp(self):
        super(TestNodeContributorAdd, self).setUp()

        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

        self.user_three = AuthUserFactory()
        self.data_user_two = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        self.data_user_three = {
            'data': {
                'id': self.user_three._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }

    def test_add_contributor_no_type(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_add_contributor_incorrect_type(self):
        data = {
            'data': {
                'type': 'Incorrect type.',
                'attributes': {
                    'id': self.user_two._id,
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.public_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_add_contributor_is_visible_by_default(self):
        del self.data_user_two['data']['attributes']['bibliographic']
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.public_project.reload()
        assert_in(self.user_two, self.public_project.contributors)
        assert_true(self.public_project.get_visible(self.user_two))

    @assert_logs(NodeLog.CONTRIB_ADDED, 'public_project')
    def test_adds_bibliographic_contributor_public_project_admin(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.public_project.reload()
        assert_in(self.user_two, self.public_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_non_bibliographic_contributor_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)
        assert_equal(res.json['data']['attributes']['bibliographic'], False)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_false(self.private_project.get_visible(self.user_two))

    def test_adds_contributor_public_project_non_admin(self):
        self.public_project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user), save=True)
        res = self.app.post_json_api(self.public_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        self.public_project.reload()
        assert_not_in(self.user_three, self.public_project.contributors)

    def test_adds_contributor_public_project_non_contributor(self):
        res = self.app.post_json_api(self.public_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_not_in(self.user_three, self.public_project.contributors)

    def test_adds_contributor_public_project_not_logged_in(self):
        res = self.app.post_json_api(self.public_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_not_in(self.user_two, self.public_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_contributor_private_project_admin(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_contributor_without_bibliographic_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {}
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_admin_contributor_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE, permissions.ADMIN])

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_write_contributor_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_read_contributor_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user_two._id)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        assert_equal(self.private_project.get_permissions(self.user_two), [permissions.READ])

    def test_adds_invalid_permission_contributor_private_project_admin(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': 'invalid',
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.private_project.reload()
        assert_not_in(self.user_two, self.private_project.contributors)

    @assert_logs(NodeLog.CONTRIB_ADDED, 'private_project')
    def test_adds_none_permission_contributor_private_project_admin_uses_default_permissions(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': None,
                    'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        self.private_project.reload()
        assert_in(self.user_two, self.private_project.contributors)
        for permission in permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS:
            assert_true(self.private_project.has_permission(self.user_two, permission))

    def test_adds_already_existing_contributor_private_project_admin(self):
        self.private_project.add_contributor(self.user_two, auth=Auth(self.user), save=True)
        self.private_project.reload()

        res = self.app.post_json_api(self.private_url, self.data_user_two,
                                 auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_adds_non_existing_user_private_project_admin(self):
        data = {
            'data': {
                'id': 'Fake',
                'type': 'contributors',
                'attributes': {
                        'bibliographic': True
                }
            }
        }
        res = self.app.post_json_api(self.private_url, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        self.private_project.reload()
        assert_equal(len(self.private_project.contributors), 1)

    def test_adds_contributor_private_project_non_admin(self):
        self.private_project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], auth=Auth(self.user))
        res = self.app.post_json_api(self.private_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_not_in(self.user_three, self.private_project.contributors)

    def test_adds_contributor_private_project_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.data_user_three,
                                 auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.private_project.reload()
        assert_not_in(self.user_three, self.private_project.contributors)

    def test_adds_contributor_private_project_not_logged_in(self):
        res = self.app.post_json_api(self.private_url, self.data_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.private_project.reload()
        assert_not_in(self.user_two, self.private_project.contributors)


class TestContributorDetail(NodeCRUDTestCase):
    def setUp(self):
        super(TestContributorDetail, self).setUp()

        self.public_url = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.public_project, self.user._id)
        self.private_url_base = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.private_project._id, '{}')
        self.private_url = self.private_url_base.format(self.user._id)

    def test_get_public_contributor_detail(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_get_private_node_contributor_detail_contributor_auth(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_get_private_node_contributor_detail_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_get_private_node_contributor_detail_not_logged_in(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_get_private_node_non_contributor_detail_contributor_auth(self):
        res = self.app.get(self.private_url_base.format(self.user_two._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_get_private_node_invalid_user_detail_contributor_auth(self):
        res = self.app.get(self.private_url_base.format('invalid'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


class TestNodeContributorUpdate(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorUpdate, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        self.url_creator = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user._id)
        self.url_contributor = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_two._id)

    def test_change_contributor_no_id(self):
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_change_contributor_incorrect_id(self):
        data = {
            'data': {
                'id': '12345',
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_change_contributor_no_type(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_change_contributor_incorrect_type(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'Wrong type.',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)


    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -3)
    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -2)
    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_change_contributor_permissions(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.ADMIN)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE, permissions.ADMIN])

        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])

        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.READ)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ])

    @assert_logs(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, 'project', -2)
    @assert_logs(NodeLog.MADE_CONTRIBUTOR_VISIBLE, 'project')
    def test_change_contributor_bibliographic(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['bibliographic'], False)

        self.project.reload()
        assert_false(self.project.get_visible(self.user_two))

        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['bibliographic'], True)

        self.project.reload()
        assert_true(self.project.get_visible(self.user_two))

    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project', -2)
    @assert_logs(NodeLog.MADE_CONTRIBUTOR_INVISIBLE, 'project')
    def test_change_contributor_permission_and_bibliographic(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.READ)
        assert_equal(attributes['bibliographic'], False)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ])
        assert_false(self.project.get_visible(self.user_two))

    @assert_not_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_not_change_contributor(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': None,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)
        assert_equal(attributes['bibliographic'], True)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    def test_invalid_change_inputs_contributor(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': 'invalid',
                    'bibliographic': 'invalid'
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    @assert_logs(NodeLog.PERMISSIONS_UPDATED, 'project')
    def test_change_admin_self_with_other_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        data = {
            'data': {
                'id': self.user._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['permission'], permissions.WRITE)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user), [permissions.READ, permissions.WRITE])

    def test_change_admin_self_without_other_admin(self):
        data = {
            'data': {
                'id': self.user._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user), [permissions.READ, permissions.WRITE, permissions.ADMIN])

    def test_remove_all_bibliographic_statuses_contributors(self):
        self.project.set_visible(self.user_two, False, save=True)
        data = {
            'data': {
                'id': self.user._id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_creator, data, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_true(self.project.get_visible(self.user))

    def test_change_contributor_non_admin_auth(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))

    def test_change_contributor_not_logged_in(self):
        data = {
            'data': {
                'id': self.user_two._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = self.app.put_json_api(self.url_contributor, data, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_equal(self.project.get_permissions(self.user_two), [permissions.READ, permissions.WRITE])
        assert_true(self.project.get_visible(self.user_two))


class TestNodeContributorDelete(ApiTestCase):
    def setUp(self):
        super(TestNodeContributorDelete, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.user_three = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.user_two, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        self.url_user = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user._id)
        self.url_user_two = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_two._id)
        self.url_user_three = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, self.user_three._id)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_contributor_admin(self):
        res = self.app.delete(self.url_user_two, auth=self.user.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_two, self.project.contributors)

    def test_remove_contributor_non_admin_is_forbidden(self):
        self.project.add_contributor(self.user_three, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        res = self.app.delete(self.url_user_three, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_in(self.user_three, self.project.contributors)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_self_non_admin(self):
        self.project.add_contributor(self.user_three, permissions=[permissions.READ, permissions.WRITE], visible=True, save=True)

        res = self.app.delete(self.url_user_three, auth=self.user_three.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_three, self.project.contributors)

    def test_remove_contributor_non_contributor(self):
        res = self.app.delete(self.url_user_two, auth=self.user_three.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        self.project.reload()
        assert_in(self.user_two, self.project.contributors)

    def test_remove_contributor_not_logged_in(self):
        res = self.app.delete(self.url_user_two, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_in(self.user_two, self.project.contributors)

    def test_remove_non_contributor_admin(self):
        assert_not_in(self.user_three, self.project.contributors)
        res = self.app.delete(self.url_user_three, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        self.project.reload()
        assert_not_in(self.user_three, self.project.contributors)

    def test_remove_non_existing_user_admin(self):
        url_user_fake = '/{}nodes/{}/contributors/{}/'.format(API_BASE, self.project._id, 'fake')
        res = self.app.delete(url_user_fake, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_remove_self_contributor_not_unique_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        res = self.app.delete(self.url_user, auth=self.user.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user, self.project.contributors)

    @assert_logs(NodeLog.CONTRIB_REMOVED, 'project')
    def test_can_remove_self_as_contributor_not_unique_admin(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        res = self.app.delete(self.url_user_two, auth=self.user_two.auth)
        assert_equal(res.status_code, 204)

        self.project.reload()
        assert_not_in(self.user_two, self.project.contributors)

    def test_remove_self_contributor_unique_admin(self):
        res = self.app.delete(self.url_user, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_in(self.user, self.project.contributors)

    def test_can_not_remove_only_bibliographic_contributor(self):
        self.project.add_permission(self.user_two, permissions.ADMIN, save=True)
        self.project.set_visible(self.user_two, False, save=True)
        res = self.app.delete(self.url_user, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.project.reload()
        assert_in(self.user, self.project.contributors)


class TestNodeRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestNodeRegistrationList, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)
        self.project.save()
        self.private_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_registration_project = RegistrationFactory(creator=self.user, project=self.public_project)
        self.public_project.save()
        self.public_url = '/{}nodes/{}/registrations/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_registrations_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['title'], self.public_project.title)

    def test_return_public_registrations_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['category'], self.public_project.category)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_private_registrations_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_return_private_registrations_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['category'], self.project.category)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_private_registrations_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


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
        assert_equal(res.status_code, 403)

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
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

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
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')


class TestNodeLinksList(ApiTestCase):

    def setUp(self):
        super(TestNodeLinksList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)

        self.user_two = AuthUserFactory()

    def test_return_public_node_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['attributes']['target_node_id'], self.public_pointer_project._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_return_public_node_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user_two.auth)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_in(res_json[0]['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_return_private_node_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_return_private_node_pointers_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res_json), 1)
        assert_in(res_json[0]['attributes']['target_node_id'], self.pointer_project._id)

    def test_return_private_node_pointers_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_deleted_links_not_returned(self):
        res = self.app.get(self.public_url, expect_errors=True)
        res_json = res.json['data']
        original_length = len(res_json)

        self.public_pointer_project.is_deleted = True
        self.public_pointer_project.save()

        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), original_length - 1)


class TestNodeTags(ApiTestCase):
    def setUp(self):
        super(TestNodeTags, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.public_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.private_project.add_contributor(self.user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

        self.one_new_tag_json = {
            'data': {
                'id': self.public_project._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }
        self.private_payload = {
            'data': {
                'id': self.private_project._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    def test_public_project_starts_with_no_tags(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

    @assert_logs(NodeLog.TAG_ADDED, 'public_project')
    def test_contributor_can_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.public_project.reload()
        assert_equal(len(self.public_project.tags), 1)
        assert_equal(self.public_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.public_url)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    @assert_logs(NodeLog.TAG_ADDED, 'private_project')
    def test_contributor_can_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure data is correct in the database
        self.private_project.reload()
        assert_equal(len(self.private_project.tags), 1)
        assert_equal(self.private_project.tags[0]._id, 'new-tag')
        # Ensure data is correct when GETting the resource again
        reload_res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(reload_res.json['data']['attributes']['tags']), 1)
        assert_equal(reload_res.json['data']['attributes']['tags'][0], 'new-tag')

    def test_non_authenticated_user_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_authenticated_user_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_non_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json_api(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)\

    @assert_logs(NodeLog.TAG_ADDED, 'private_project', -4)
    @assert_logs(NodeLog.TAG_ADDED, 'private_project', -3)
    @assert_logs(NodeLog.TAG_REMOVED, 'private_project', -2)
    @assert_logs(NodeLog.TAG_REMOVED, 'private_project')
    def test_tags_add_and_remove_properly(self):
        res = self.app.patch_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure adding tag data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure removing and adding tag data is correct from the PATCH response
        res = self.app.patch_json_api(self.private_url, {'data': {'id': self.private_project._id, 'type':'nodes', 'attributes': {'tags':['newer-tag']}}}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'newer-tag')
        # Ensure removing tag data is correct from the PATCH response
        res = self.app.patch_json_api(self.private_url, {'data': {'id': self.private_project._id, 'type':'nodes', 'attributes': {'tags': []}}}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)


class TestNodeLinkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeLinkCreate, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)

        self.private_payload = {
            'data': {
                "type": "node_links",
                "attributes": {
                    "target_node_id": self.pointer_project._id
                }
            }
        }

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)
        self.public_payload = {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.public_pointer_project._id}}}
        self.fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'fdxlq')
        self.fake_payload = {'data': {'type': 'node_links', 'attributes': {'target_node_id': 'fdxlq'}}}
        self.point_to_itself_payload = {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.public_project._id}}}

        self.user_two = AuthUserFactory()
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.user_two_project._id)
        self.user_two_payload = {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.user_two_project._id}}}

    def test_creates_project_target_not_nested(self):
        payload = {'data': {'type': 'node_links', 'target_node_id': self.pointer_project._id}}
        res = self.app.post_json_api(self.public_url, payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes')
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')

    def test_creates_public_node_pointer_logged_out(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_creates_public_node_pointer_logged_in(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_creates_private_node_pointer_logged_out(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['target_node_id'], self.pointer_project._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_create_node_pointer_non_contributing_node_to_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'project')
    def test_create_node_pointer_contributing_node_to_non_contributing_node(self):
        res = self.app.post_json_api(self.private_url, self.user_two_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.user_two_project._id)

    def test_create_pointer_non_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_create_pointer_contributing_node_to_fake_node(self):
        res = self.app.post_json_api(self.private_url, self.fake_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_create_fake_node_pointing_to_contributing_node(self):
        res = self.app.post_json_api(self.fake_url, self.private_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

        res = self.app.post_json_api(self.fake_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_create_node_pointer_to_itself(self):
        res = self.app.post_json_api(self.public_url, self.point_to_itself_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_project._id)

    def test_create_node_pointer_to_itself_unauthorized(self):
        res = self.app.post_json_api(self.public_url, self.point_to_itself_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_CREATED, 'public_project')
    def test_create_node_pointer_already_connected(self):
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])

    def test_cannot_add_link_to_registration(self):
        registration = RegistrationFactory(creator=self.user)

        url = '/{}nodes/{}/node_links/'.format(API_BASE, registration._id)
        payload = {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.public_pointer_project._id}}}
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_node_pointer_no_type(self):
        payload = {'data': {'attributes': {'target_node_id': self.user_two_project._id}}}
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be null.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_node_pointer_incorrect_type(self):
        payload = {'data': {'type': 'Wrong type.', 'attributes': {'target_node_id': self.user_two_project._id}}}
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')


class TestNodeFilesList(ApiTestCase):

    def setUp(self):
        super(TestNodeFilesList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.private_url = '/{}nodes/{}/files/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_url = '/{}nodes/{}/files/'.format(API_BASE, self.public_project._id)

    def test_returns_public_files_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_returns_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_returns_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = model.AddonGitHubOauthSettings(github_user_id='plstowork', oauth_access_token='foo')
        oauth_settings.save()
        user_settings = model.AddonGitHubUserSettings(oauth_settings=oauth_settings)
        user_settings.save()
        addon.user_settings = user_settings
        addon.save()
        self.project.save()
        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        providers = [item['attributes']['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)

    @mock.patch('api.nodes.views.requests.get')
    def test_returns_node_files_list(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': [{
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/',
                u'provider': u'github',
                u'size': None,
                u'materialized': '/',
            }]
        }
        auth_header = 'Basic {}'.format(base64.b64encode(':'.join(self.user.auth)))
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')
        mock_waterbutler_request.assert_called_once_with(
            'http://localhost:7777/v1/resources/{}/providers/github/?meta=True'.format(self.project._id),
            cookies={'foo':'bar'},
            headers={'Authorization': auth_header}
        )

    @mock.patch('api.nodes.views.requests.get')
    def test_handles_unauthenticated_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 401
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])


    @mock.patch('api.nodes.views.requests.get')
    def test_handles_bad_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 418
        mock_res.json.return_value = {}
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('detail', res.json['errors'][0])

    def test_files_list_contains_relationships_object(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert 'relationships' in res.json['data'][0]


class TestNodeLinkDetail(ApiTestCase):

    def setUp(self):
        super(TestNodeLinkDetail, self).setUp()
        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer = self.private_project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.private_project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True)
        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}/'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_returns_public_node_pointer_detail_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        res_json = res.json['data']
        assert_equal(res_json['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_returns_public_node_pointer_detail_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res_json['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_returns_private_node_pointer_detail_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_node_pointer_detail_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res_json['attributes']['target_node_id'], self.pointer_project._id)

    def test_returns_private_node_pointer_detail_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])


class TestDeleteNodeLink(ApiTestCase):

    def setUp(self):
        super(TestDeleteNodeLink, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True)
        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/{}nodes/{}/node_links/{}'.format(API_BASE, self.project._id, self.pointer._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project,
                                                              auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/{}nodes/{}/node_links/{}'.format(API_BASE, self.public_project._id, self.public_pointer._id)

    def test_cannot_delete_if_registration(self):
        registration = RegistrationFactory(project=self.public_project)

        url = '/{}nodes/{}/node_links/'.format(
            API_BASE,
            registration._id,
        )
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        pointer_id = res.json['data'][0]['id']

        url = '/{}nodes/{}/node_links/{}'.format(
            API_BASE,
            registration._id,
            pointer_id,
        )
        res = self.app.delete(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_deletes_public_node_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0].keys())

    def test_deletes_public_node_pointer_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user_two.auth, expect_errors=True)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])
        self.public_project.reload()
        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_deletes_public_node_pointer_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_project.nodes_pointer))

    def test_deletes_private_node_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_deletes_private_node_pointer_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)

    def test_deletes_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @assert_logs(NodeLog.POINTER_REMOVED, 'public_project')
    def test_return_deleted_public_node_pointer(self):
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload() # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    @assert_logs(NodeLog.POINTER_REMOVED, 'project')
    def test_return_deleted_private_node_pointer(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    # Regression test for https://openscience.atlassian.net/browse/OSF-4322
    def test_delete_link_that_is_not_linked_to_correct_node(self):
        project = ProjectFactory(creator=self.user)
        # The node link belongs to a different project
        res = self.app.delete(
            '/{}nodes/{}/node_links/{}'.format(API_BASE, project._id, self.public_pointer._id),
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)
        errors = res.json['errors']
        assert_equal(len(errors), 1)
        assert_equal(errors[0]['detail'], 'Node link does not belong to the requested node.')


class TestReturnDeletedNode(ApiTestCase):
    def setUp(self):

        super(TestReturnDeletedNode, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.public_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                             title='This public project has been deleted', category='project',
                                             is_public=True)
        self.private_deleted = ProjectFactory(is_deleted=True, creator=self.user,
                                              title='This private project has been deleted', category='project',
                                              is_public=False)
        self.private = ProjectFactory(is_public=False, creator=self.user, title='A boring project', category='project')
        self.public = ProjectFactory(is_public=True, creator=self.user, title='A fun project', category='project')

        self.new_title = 'This deleted node has been edited'

        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_deleted._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_deleted._id)

    def test_return_deleted_public_node(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_return_deleted_private_node(self):
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_public_node(self):
        res = self.app.put_json_api(self.public_url, params={'title': self.new_title,
                                                    'node_id': self.public_deleted._id,
                                                    'category': self.public_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_private_node(self):
        res = self.app.put_json_api(self.private_url, params={'title': self.new_title,
                                                     'node_id': self.private_deleted._id,
                                                     'category': self.private_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_public_node(self):
        res = self.app.delete(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_delete_deleted_private_node(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)


class TestExceptionFormatting(ApiTestCase):
    def setUp(self):

        super(TestExceptionFormatting, self).setUp()
        self.user = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.project_no_title = {
            'data': {
                'attributes': {
                    'description': self.description,
                    'category': self.category,
                    'type': 'nodes',
                }
            }
        }

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_creates_project_with_no_title_formatting(self):
        url = '/{}nodes/'.format(API_BASE)
        res = self.app.post_json_api(url, self.project_no_title, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/attributes/title'})
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')

    def test_node_does_not_exist_formatting(self):
        url = '/{}nodes/{}/'.format(API_BASE, '12345')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'Not found.'})

    def test_forbidden_formatting(self):
        res = self.app.get(self.private_url, auth=self.non_contrib.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': 'You do not have permission to perform this action.'})

    def test_not_authorized_formatting(self):
        res = self.app.get(self.private_url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(errors[0], {'detail': "Authentication credentials were not provided."})

    def test_update_project_with_no_title_or_category_formatting(self):
        res = self.app.put_json_api(self.private_url, {'data': {'type': 'nodes', 'id': self.private_project._id, 'attributes': {'description': 'New description'}}}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(len(errors), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/attributes/category'}, {'pointer': '/data/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field is required.', 'This field is required.'])

    def test_create_node_link_no_target_formatting(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {'data': {'type': 'node_links', 'attributes': {'target_node_id': ''}}},
                                     auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/attributes/target_node_id'})
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')

    def test_node_link_already_exists(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.public_project._id}}}, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        res = self.app.post_json_api(url, {'data': {'type': 'node_links', 'attributes': {'target_node_id': self.public_project._id}}}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert(self.public_project._id in res.json['errors'][0]['detail'])
