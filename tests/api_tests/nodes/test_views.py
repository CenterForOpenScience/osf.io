# -*- coding: utf-8 -*-
import mock
from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from website.models import Node
from website.views import find_dashboard
from framework.auth.core import Auth
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
        res = self.app.get(self.url)
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
        assert_equal(errors[0]['detail'], 'Querystring contains an invalid filter.')


class TestNodeCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {'title': self.title,
                               'description': self.description,
                               'category': self.category,
                               'public': True}
        self.private_project = {'title': self.title,
                                'description': self.description,
                                'category': self.category,
                                'public': False}

    def test_creates_public_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.public_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_creates_public_project_logged_in(self):
        res = self.app.post_json_api(self.url, self.public_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.public_project['title'])
        assert_equal(res.json['data']['attributes']['description'], self.public_project['description'])
        assert_equal(res.json['data']['attributes']['category'], self.public_project['category'])
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_project_logged_out(self):
        res = self.app.post_json_api(self.url, self.private_project, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_creates_private_project_logged_in_contributor(self):
        res = self.app.post_json_api(self.url, self.private_project, auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.private_project['title'])
        assert_equal(res.json['data']['attributes']['description'], self.private_project['description'])
        assert_equal(res.json['data']['attributes']['category'], self.private_project['category'])

    def test_creates_project_creates_project_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'
        description = 'An <script>alert("even cooler")</script> project'

        res = self.app.post_json_api(self.url, {
            'title': title,
            'description': description,
            'category': self.category,
            'public': True,
        }, auth=self.user_one.auth)
        project_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        url = '/{}nodes/{}/'.format(API_BASE, project_id)

        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], self.category)


class TestNodeBulkCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeBulkCreate, self).setUp()
        self.user_one = AuthUserFactory()
        self.url = '/{}nodes/'.format(API_BASE)

        self.title = 'Cool Project'
        self.description = 'A Properly Cool Project'
        self.category = 'data'

        self.user_two = AuthUserFactory()

        self.public_project = {'title': self.title,
                               'description': self.description,
                               'category': self.category,
                               'public': True}
        self.private_project = {'title': self.title,
                                'description': self.description,
                                'category': self.category,
                                'public': False}

        self.empty_project = {'title': "", 'description': "", "category": ""}

    def test_bulk_create_logged_in(self):
        res = self.app.post_json_api(self.url, [self.public_project, self.private_project], auth=self.user_one.auth)
        assert_equal(res.status_code, 201)
        assert_equal(len(res.json['data']), 2)
        assert_equal(res.json['data'][0]['attributes']['title'], self.public_project['title'])
        assert_equal(res.json['data'][1]['attributes']['title'], self.private_project['title'])
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 2)

    def test_bulk_create_all_or_nothing(self):
        res = self.app.post_json_api(self.url, [self.public_project, self.empty_project], auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.url, auth=self.user_one.auth)
        assert_equal(len(res.json['data']), 0)

    def test_bulk_create_logged_out(self):
        res = self.app.post_json_api(self.url, [self.public_project, self.private_project], expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_bulk_create_error_formatting(self):
        res = self.app.post_json_api(self.url, [self.empty_project, self.empty_project], auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/attributes/title'}, {'pointer': '/data/attributes/title'}])
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ["This field may not be blank.", "This field may not be blank."])
        assert_equal(res.json['meta'], [self.empty_project]*2)

    def test_bulk_create_limits(self):
        node_create_list = [self.public_project] * 11
        res = self.app.post_json_api(self.url, node_create_list, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')


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

        self.public_payload = [
            {
                'id': self.public_project._id,
                'title': self.new_title,
                'description': self.new_description,
                'category': self.new_category,
                'public': True
            },
            {
                'id': self.public_project_two._id,
                'title': self.new_title,
                'description': self.new_description,
                'category': self.new_category,
                'public': True
            }
        ]

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

        self.private_payload = [
            {
                'id': self.private_project._id,
                'title': self.new_title,
                'description': self.new_description,
                'category': self.new_category,
                'public': False
            },
            {
                'id': self.private_project_two._id,
                'title': self.new_title,
                'description': self.new_description,
                'category': self.new_category,
                'public': False
            }
        ]

        self.empty_payload = [
            {'id': self.public_project._id, 'title': "", 'description': "", "category": ""},
            {'id': self.public_project_two._id, 'title': "", 'description': "", "category": ""}
        ]

    def test_update_public_projects_one_not_found(self):
        empty_payload = [
            {
            'id': 12345,
            'title': self.new_title,
            'category': self.new_category
            },
            self.public_payload[0]
        ]
        res = self.app.put_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)


    def test_update_public_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_update_public_projects_logged_in(self):
        res = self.app.put_json_api(self.url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_update_private_projects_logged_out(self):
        res = self.app.put_json_api(self.url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_update_private_projects_logged_in_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_update_private_projects_logged_in_non_contrib(self):
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=['read'])
        self.private_project_two.add_contributor(self.user_two, permissions=['read'])
        res = self.app.put_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_update_projects_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.url, {'id': self.public_project._id, 'title': self.new_title, 'category': "project"},
                                    auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_update_error_formatting(self):
        res = self.app.put_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True)
        print [res.json['errors'][0]['detail'], res.json['errors'][1]['detail']]
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/attributes/title'}]*2)
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.']*2)
        assert_equal(res.json['meta'], self.empty_payload)

    def test_bulk_update_id_not_supplied(self):
        res = self.app.put_json_api(self.url, [{'title': self.new_title, 'category': self.new_category}], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/id')
        assert_equal(res.json['errors'][0]['detail'], "This field is required.")

    def test_bulk_update_limits(self):
        node_update_list = [self.public_payload[0]] * 11
        res = self.app.put_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')


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

        self.public_payload = [
            {
                'id': self.public_project._id,
                'title': self.new_title,
            },
            {
                'id': self.public_project_two._id,
                'title': self.new_title,
            }
        ]

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

        self.private_payload = [
            {
                'id': self.private_project._id,
                'title': self.new_title,
            },
            {
                'id': self.private_project_two._id,
                'title': self.new_title,
            }
        ]

        self.empty_payload = [
            {'id': self.public_project._id, 'title': ""},
            {'id': self.public_project_two._id, 'title': ""}
        ]

    def test_partial_update_public_projects_one_not_found(self):
        empty_payload = [
            {
            'id': 12345,
            'title': self.new_title
            },
            self.public_payload[0]
        ]
        res = self.app.patch_json_api(self.url, empty_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_partial_update_public_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")

        url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.public_project_two._id)

        res = self.app.get(url)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_partial_update_public_projects_logged_in(self):
        res = self.app.patch_json_api(self.url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal({self.public_project._id, self.public_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_partial_update_private_projects_logged_out(self):
        res = self.app.patch_json_api(self.url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_partial_update_private_projects_logged_in_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal({self.private_project._id, self.private_project_two._id},
                     {res.json['data'][0]['id'], res.json['data'][1]['id']})
        assert_equal(res.json['data'][0]['attributes']['title'], self.new_title)
        assert_equal(res.json['data'][1]['attributes']['title'], self.new_title)

    def test_partial_update_private_projects_logged_in_non_contrib(self):
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_partial_update_private_projects_logged_in_read_only_contrib(self):
        self.private_project.add_contributor(self.user_two, permissions=['read'])
        self.private_project_two.add_contributor(self.user_two, permissions=['read'])
        res = self.app.patch_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)
        url_two = '/{}nodes/{}/'.format(API_BASE, self.private_project_two._id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

        res = self.app.get(url_two, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], self.title)

    def test_bulk_partial_update_projects_send_dictionary_not_list(self):
        res = self.app.put_json_api(self.url, {'id': self.public_project._id, 'title': self.new_title, 'category': "project"},
                                    auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Expected a list of items but got type "dict".')

    def test_bulk_partial_update_error_formatting(self):
        res = self.app.patch_json_api(self.url, self.empty_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = res.json['errors']
        assert_items_equal([errors[0]['source'], errors[1]['source']],
                           [{'pointer': '/data/attributes/title'}]*2)
        assert_items_equal([errors[0]['detail'], errors[1]['detail']],
                           ['This field may not be blank.']*2)

    def test_bulk_partial_update_id_not_supplied(self):
        res = self.app.patch_json_api(self.url, [{'title': self.new_title}], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Must supply id.')

    def test_bulk_partial_update_limits(self):
        node_update_list = [self.public_payload[0]] * 11
        res = self.app.patch_json_api(self.url, node_update_list, auth=self.user.auth, expect_errors=True)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')


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

        self.public_payload = [{'id': self.project_one._id}, {'id': self.project_two._id}]
        self.private_payload = [{'id': self.private_project_user_one._id}]

    def test_bulk_delete_public_projects_logged_in(self):
        res = self.app.delete_json_api(self.url, self.public_payload, auth=self.user_one.auth)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.project_one_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.project_one.reload()
        self.project_two.reload()

    def test_bulk_delete_public_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_bulk_delete_private_projects_logged_out(self):
        res = self.app.delete_json_api(self.url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_bulk_delete_private_projects_logged_in_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 204)

        res = self.app.get(self.private_project_url, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 410)
        self.private_project_user_one.reload()

    def test_bulk_delete_private_projects_logged_in_non_contributor(self):
        res = self.app.delete_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_private_projects_logged_in_read_only_contributor(self):
        self.private_project_user_one.add_contributor(self.user_two, permissions=['read'])
        self.private_project_user_one.save()
        res = self.app.delete_json_api(self.url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_all_or_nothing(self):
        new_payload = [{'id': self.private_project_user_one._id}, {'id': self.private_project_user_two._id}]
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

        res = self.app.get(self.private_project_url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)

        url = "/{}nodes/{}/".format(API_BASE, self.private_project_user_two._id)
        res = self.app.get(url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)

    def test_bulk_delete_limits(self):
        new_payload = [{'id': self.private_project_user_one._id}]*11
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Bulk operation limit is 10, got 11.')

    def test_bulk_delete_not_found(self):
        new_payload = [{'id': '12345'}]
        res = self.app.delete_json_api(self.url, new_payload, auth=self.user_one.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


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
        assert 'detail' in res.json['errors'][0]


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
        assert 'detail' in res.json['errors'][0]

    def test_top_level_project_has_no_parent(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['relationships']['parent']['links']['self'], None)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_child_project_has_parent(self):
        public_component = NodeFactory(parent=self.public_project, creator=self.user, is_public=True)
        public_component_url = '/{}nodes/{}/'.format(API_BASE, public_component._id)
        res = self.app.get(public_component_url)
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['parent']['links']['self']
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
        url = res.json['data']['relationships']['files']['links']['related']
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


class TestNodeUpdate(ApiTestCase):

    def setUp(self):
        super(TestNodeUpdate, self).setUp()
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
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.private_project = ProjectFactory(title=self.title,
                                              description=self.description,
                                              category=self.category,
                                              is_public=False,
                                              creator=self.user)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_update_public_project_logged_out(self):
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]


    def test_update_public_project_logged_in(self):
        # Public project, logged in, contrib
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

        # Public project, logged in, unauthorized
        res = self.app.put_json_api(self.public_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_update_private_project_logged_out(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_update_private_project_logged_in_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.new_description)
        assert_equal(res.json['data']['attributes']['category'], self.new_category)

    def test_update_private_project_logged_in_non_contributor(self):
        res = self.app.put_json_api(self.private_url, {
            'title': self.new_title,
            'description': self.new_description,
            'category': self.new_category,
            'public': False,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_update_project_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        project = self.project = ProjectFactory(
            title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)

        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.put_json_api(url, {
            'title': new_title,
            'description': new_description,
            'category': self.new_category,
            'public': True,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(new_description))

    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        project = self.project = ProjectFactory(
            title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)

        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.patch_json_api(url, {
            'title': new_title,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], strip_html(new_title))
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_writing_to_public_field(self):
        title = "Cool project"
        description = 'A Properly Cool Project'
        category = 'data'
        project = self.project = ProjectFactory(
            title=title, description=description, category=category, is_public=True, creator=self.user)
        # Test non-contrib writing to public field
        url = '/{}nodes/{}/'.format(API_BASE, project._id)
        res = self.app.patch_json_api(url, {
            'public': False,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        # Test creator writing to public field (supposed to be read-only)
        res = self.app.patch_json_api(url, {
            'public': False,
        }, auth=self.user.auth, expect_errors=True)
        assert_true(res.json['data']['attributes']['public'])
        # django returns a 200 on PATCH to read only field, even though it does not update the field.
        assert_equal(res.status_code, 200)

    def test_partial_update_public_project_logged_out(self):
        res = self.app.patch_json_api(self.public_url, {'title': self.new_title}, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_public_project_logged_in(self):
        res = self.app.patch_json_api(self.public_url, {
            'title': self.new_title,
        }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

        # Public resource, logged in, unauthorized
        res = self.app.patch_json_api(self.public_url, {
            'title': self.new_title,
        }, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_private_project_logged_out(self):
        res = self.app.patch_json_api(self.private_url, {'title': self.new_title}, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_private_project_logged_in_contributor(self):
        res = self.app.patch_json_api(self.private_url, {'title': self.new_title}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['title'], self.new_title)
        assert_equal(res.json['data']['attributes']['description'], self.description)
        assert_equal(res.json['data']['attributes']['category'], self.category)

    def test_partial_update_private_project_logged_in_non_contributor(self):
        res = self.app.patch_json_api(self.private_url,
                                  {'title': self.new_title},
                                  auth=self.user_two.auth,
                                  expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


class TestNodeDelete(ApiTestCase):

    def setUp(self):
        super(TestNodeDelete, self).setUp()
        self.user = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)

        self.fake_url = '/{}nodes/{}/'.format(API_BASE, '12345')

    def test_deletes_public_node_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_public_node_fails_if_bad_auth(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.public_project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_public_node_succeeds_as_owner(self):
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.public_project.is_deleted, True)

    def test_deletes_private_node_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(self.project.is_deleted, True)

    def test_deletes_private_node_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.project.is_deleted, False)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_read_only_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read'])
        self.project.save()
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        self.project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(self.project.is_deleted, False)
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


class TestNodeContributorList(ApiTestCase):

    def setUp(self):
        super(TestNodeContributorList, self).setUp()
        self.user = AuthUserFactory()

        self.user_two = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.private_project._id)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/contributors/'.format(API_BASE, self.public_project._id)

    def test_return_public_contributor_list_logged_out(self):
        self.public_project.add_contributor(self.user_two)
        self.public_project.save()

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
        assert_equal(errors[0]['detail'], 'Querystring contains an invalid filter.')


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
        self.project.add_contributor(self.user, permissions=['read', 'write'])
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


class TestNodeChildCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeChildCreate, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.project = ProjectFactory(creator=self.user, is_publc=True)

        self.url = '/{}nodes/{}/children/'.format(API_BASE, self.project._id)
        self.child = {
            'title': 'child',
            'description': 'this is a child project',
            'category': 'project',
        }

    def test_creates_child_logged_out_user(self):
        res = self.app.post_json_api(self.url, self.child, expect_errors=True)
        assert_equal(res.status_code, 401)

        self.project.reload()
        assert_equal(len(self.project.nodes), 0)

    def test_creates_child_logged_in_owner(self):
        res = self.app.post_json_api(self.url, self.child, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['category'])

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)

    def test_creates_child_logged_in_write_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)

        res = self.app.post_json_api(self.url, self.child, auth=self.user_two.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['title'], self.child['title'])
        assert_equal(res.json['data']['attributes']['description'], self.child['description'])
        assert_equal(res.json['data']['attributes']['category'], self.child['category'])

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)

    def test_creates_child_logged_in_read_contributor(self):
        self.project.add_contributor(self.user_two, permissions=['read'], auth=Auth(self.user), save=True)
        self.project.reload()

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
            'title': title,
            'description': description,
            'category': 'project',
            'public': True,
        }, auth=self.user.auth)
        child_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/{}nodes/{}/'.format(API_BASE, child_id)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data']['attributes']['title'], strip_html(title))
        assert_equal(res.json['data']['attributes']['description'], strip_html(description))
        assert_equal(res.json['data']['attributes']['category'], 'project')

        self.project.reload()
        assert_equal(res.json['data']['id'], self.project.nodes[0]._id)


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
        assert 'detail' in res.json['errors'][0]

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
        assert 'detail' in res.json['errors'][0]


class TestNodeTags(ApiTestCase):
    def setUp(self):
        super(TestNodeTags, self).setUp()
        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()
        self.one_new_tag_json = {'tags': ['new-tag']}

        self.public_project = ProjectFactory(title="Project One", is_public=True, creator=self.user)
        self.public_project.add_contributor(self.user, permissions=['read'])
        self.private_project = ProjectFactory(title="Project Two", is_public=False, creator=self.user)
        self.private_project.add_contributor(self.user, permissions=['read'])
        self.public_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/'.format(API_BASE, self.private_project._id)

    def test_public_project_starts_with_no_tags(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)

    def test_contributor_can_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, auth=self.user.auth)
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

    def test_contributor_can_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, auth=self.user.auth)
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
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_authenticated_user_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=None)
        assert_equal(res.status_code, 401)

    def test_non_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_non_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=self.user_two.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_public_project(self):
        res = self.app.patch_json(self.public_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)

    def test_read_only_contributor_cannot_add_tag_to_private_project(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, expect_errors=True, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 403)

    def test_tags_add_and_remove_properly(self):
        res = self.app.patch_json(self.private_url, self.one_new_tag_json, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # Ensure adding tag data is correct from the PATCH response
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'new-tag')
        # Ensure removing and adding tag data is correct from the PATCH response
        res = self.app.patch_json(self.private_url, {'tags': ['newer-tag']}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 1)
        assert_equal(res.json['data']['attributes']['tags'][0], 'newer-tag')
        # Ensure removing tag data is correct from the PATCH response
        res = self.app.patch_json(self.private_url, {'tags': []}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']['attributes']['tags']), 0)


class TestCreateNodeLink(ApiTestCase):
    def setUp(self):
        super(TestCreateNodeLink, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.project._id)
        self.private_payload = {'target_node_id': self.pointer_project._id}
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.public_project._id)
        self.public_payload = {'target_node_id': self.public_pointer_project._id}
        self.fake_url = '/{}nodes/{}/node_links/'.format(API_BASE, 'fdxlq')
        self.fake_payload = {'target_node_id': 'fdxlq'}
        self.point_to_itself_payload = {'target_node_id': self.public_project._id}

        self.user_two = AuthUserFactory()
        self.user_two_project = ProjectFactory(is_public=True, creator=self.user_two)
        self.user_two_url = '/{}nodes/{}/node_links/'.format(API_BASE, self.user_two_project._id)
        self.user_two_payload = {'target_node_id': self.user_two_project._id}

    def test_creates_public_node_pointer_logged_out(self):
        res = self.app.post(self.public_url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_creates_public_node_pointer_logged_in(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

    def test_creates_private_node_pointer_logged_out(self):
        res = self.app.post(self.private_url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]


    def test_creates_private_node_pointer_logged_in_contributor(self):
        res = self.app.post(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['target_node_id'], self.pointer_project._id)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_creates_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.post(self.private_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_non_contributing_node_to_contributing_node(self):
        res = self.app.post(self.private_url, self.user_two_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_contributing_node_to_non_contributing_node(self):
        res = self.app.post(self.private_url, self.user_two_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.user_two_project._id)

    def test_create_pointer_non_contributing_node_to_fake_node(self):
        res = self.app.post(self.private_url, self.fake_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_create_pointer_contributing_node_to_fake_node(self):
        res = self.app.post(self.private_url, self.fake_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_create_fake_node_pointing_to_contributing_node(self):
        res = self.app.post(self.fake_url, self.private_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.fake_url, self.private_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert 'detail' in res.json['errors'][0]

    def test_create_node_pointer_to_itself(self):
        res = self.app.post(self.public_url, self.point_to_itself_payload, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        res = self.app.post(self.public_url, self.point_to_itself_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_project._id)

    def test_create_node_pointer_already_connected(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['target_node_id'], self.public_pointer_project._id)

        res = self.app.post(self.public_url, self.public_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert 'detail' in res.json['errors'][0]


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
        assert 'detail' in res.json['errors'][0]

    def test_returns_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

    def test_returns_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

        self.project.add_addon('github', auth=user_auth)
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
                u'provider': u'osfstorage',
                u'size': None
            }]
        }
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    @mock.patch('api.nodes.views.requests.get')
    def test_handles_unauthenticated_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 401
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    @mock.patch('api.nodes.views.requests.get')
    def test_handles_bad_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/?path=%2F&provider=osfstorage'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 418
        mock_res.json.return_value = {}
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert 'detail' in res.json['errors'][0]

    def test_files_list_does_not_contain_empty_relationships_object(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert 'relationships' not in res.json['data'][0]


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
        assert 'detail' in res.json['errors'][0]

    def test_returns_private_node_pointer_detail_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res_json['attributes']['target_node_id'], self.pointer_project._id)

    def returns_private_node_pointer_detail_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


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

    def test_deletes_public_node_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0].keys()

    def test_deletes_public_node_pointer_fails_if_bad_auth(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user_two.auth, expect_errors=True)
        self.public_project.reload()
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]

        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

    def test_deletes_public_node_pointer_succeeds_as_owner(self):
        node_count_before = len(self.public_project.nodes_pointer)
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload()
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_project.nodes_pointer))

    def test_deletes_private_node_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_pointer_logged_in_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user.auth)
        self.project.reload()  # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)
        assert_equal(len(self.project.nodes_pointer), 0)

    def test_deletes_private_node_pointer_logged_in_non_contributor(self):
        res = self.app.delete(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert 'detail' in res.json['errors'][0]


    def test_return_deleted_public_node_pointer(self):
        res = self.app.delete(self.public_url, auth=self.user.auth)
        self.public_project.reload() # Update the model to reflect changes made by post request
        assert_equal(res.status_code, 204)

        #check that deleted pointer can not be returned
        res = self.app.get(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

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
        res = self.app.put(self.public_url, params={'title': self.new_title,
                                                    'node_id': self.public_deleted._id,
                                                    'category': self.public_deleted.category},
                           auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_edit_deleted_private_node(self):
        res = self.app.put(self.private_url, params={'title': self.new_title,
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

        self.project_no_title = {'description': self.description,
                                 'category': self.category,
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
        res = self.app.put_json_api(self.private_url, {'description': 'New description'}, auth=self.user.auth, expect_errors=True)
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
        res = self.app.post_json_api(url, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert_equal(res.json['errors'][0]['source'], {'pointer': '/data/attributes/target_node_id'})
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')

    def test_node_link_already_exists(self):
        url = self.private_url + 'node_links/'
        res = self.app.post_json_api(url, {'target_node_id': self.public_project._id}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        res = self.app.post_json_api(url, {'target_node_id': self.public_project._id}, auth=self.user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert(self.public_project._id in res.json['errors'][0]['detail'])
