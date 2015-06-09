# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from website.util.sanitize import strip_html

from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory, NodeFactory

class TestCollectionsList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.non_contrib = UserFactory.build()
        self.non_contrib.set_password('justapoorboy')
        self.non_contrib.save()
        self.basic_non_contrib_auth = (self.non_contrib.username, 'justapoorboy')

        self.deleted = ProjectFactory(is_deleted=True, is_folder=True)
        self.private = ProjectFactory(is_public=False, creator=self.user, is_folder=True)
        self.public = ProjectFactory(is_public=True, creator=self.user, is_folder=True)
        self.url = '/v2/collections/'

    def test_only_returns_non_deleted_public_projects(self):
        res = self.app.get(self.url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public._id, ids)
        assert_not_in(self.deleted._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_collection_list_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_public_collection_list_logged_in_user(self):
        res = self.app.get(self.url, auth=self.non_contrib)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_collection_list_logged_out_user(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

        Node.remove()

class TestCollectionFiltering(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.save()
        self.basic_auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')
        self.project_one = ProjectFactory(title="Project One", is_public=True, is_folder=True)
        self.project_two = ProjectFactory(title="Project Two", is_folder=True, is_public=True)
        self.project_three = ProjectFactory(title="Three", is_public=True, is_folder=True)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False,
                                                       is_folder=True, creator=self.user_one)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False,
                                                       is_folder=True, creator=self.user_two)
        self.folder = FolderFactory()
        self.dashboard = DashboardFactory()

        self.url = "/v2/collections/"

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_get_all_projects_with_no_filter_logged_in(self):
        res = self.app.get(self.url, auth=self.basic_auth_one)
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
        url = "/v2/collections/?filter[title]=Project%20One"

        res = self.app.get(url, auth=self.basic_auth_one)
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
        url = "/v2/collections/?filter[title]=Project%20One"

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
        url = "/v2/collections/?filter[title]=Two"

        res = self.app.get(url, auth=self.basic_auth_one)
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
        url = "/v2/collections/?filter[title]=Two"

        res = self.app.get(url, auth=self.basic_auth_one)
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
        url = "/v2/collections/?filter[title]=Project"

        res = self.app.get(url, auth=self.basic_auth_one)
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
        url = "/v2/collections/?filter[title]=Project"

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

    def test_incorrect_filtering_field_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/v2/collections/?filter[notafield]=bogus"

        res = self.app.get(url, auth=self.basic_auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

    def test_incorrect_filtering_field_not_logged_in(self):
        # TODO Change to check for error when the functionality changes. Currently acts as though it doesn't exist
        url = "/v2/collections/?filter[notafield]=bogus"

        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.project_one._id, ids)
        assert_in(self.project_two._id, ids)
        assert_in(self.project_three._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.dashboard._id, ids)

class TestCollectionCreate(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.url = '/v2/collections/'

        self.title = 'Cool Project'
        self.category = 'data'

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_folder = {'title': self.title, 'public': True, 'is_folder': True}
        self.private_folder = {'title': self.title, 'is_folder': True, 'public': False}

    def test_creates_public_project_logged_out(self):
        res = self.app.post_json(self.url, self.public_folder, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_public_project_logged_in(self):
        res = self.app.post_json(self.url, self.public_folder, auth=self.basic_auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.public_folder['title'])

    def test_creates_private_project_logged_out(self):
        res = self.app.post_json(self.url, self.private_folder, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_private_project_logged_in_contributor(self):
        res = self.app.post_json(self.url, self.private_folder, auth=self.basic_auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['title'], self.private_folder['title'])

    def test_creates_project_creates_project_and_sanitizes_html(self):
        title = '<em>Cool</em> <strong>Project</strong>'

        res = self.app.post_json(self.url, {
            'title': title,
            'public': True,
            'is_folder': True,
        }, auth=self.basic_auth)
        project_id = res.json['data']['id']
        assert_equal(res.status_code, 201)
        url = '/v2/collections/{}/'.format(project_id)
        res = self.app.get(url, auth=self.basic_auth)
        assert_equal(res.json['data']['title'], strip_html(title))
        # on

class TestCollectionDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_folder = ProjectFactory(title="Project One", is_public=True, is_folder=True, creator=self.user)
        self.private_folder = ProjectFactory(title="Project Two", is_public=False, is_folder=True, creator=self.user)
        self.public_url = '/v2/collections/{}/'.format(self.public_folder._id)
        self.private_url = '/v2/collections/{}/'.format(self.private_folder._id)

    def test_return_public_project_details_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.public_folder.title)

    def test_return_public_project_details_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.public_folder.title)

    def test_return_private_project_details_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
        print(vars(res))

class TestCollectionUpdate(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')

        self.title = 'Cool Project'
        self.new_title = 'Super Cool Project'

        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'justapoorboy')

        self.public_project = ProjectFactory(title=self.title, is_public=True, creator=self.user, is_folder=True)
        self.public_url = '/v2/collections/{}/'.format(self.public_project._id)

        self.private_project = ProjectFactory(title=self.title, is_public=False, creator=self.user)
        self.private_url = '/v2/collections/{}/'.format(self.private_project._id, is_folder=True)

    def test_update_public_project_logged_out(self):
        res = self.app.put_json(self.public_url, {
            'title': self.new_title,
            'public': True,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_public_project_logged_in(self):
        # Public project, logged in, contrib
        res = self.app.put_json(self.public_url, {
            'title': self.new_title,
            'public': True,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

        # Public project, logged in, unauthorized
        res = self.app.put_json(self.public_url, {
            'title': self.new_title,
            'public': True,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_update_private_project_logged_out(self):
        res = self.app.put_json(self.private_url, {
            'title': self.new_title,
            'public': False,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_project_sanitizes_html_properly(self):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        project = self.project = ProjectFactory(
            title=self.title, is_folder=True, is_public=True, creator=self.user)

        url = '/v2/collections/{}/'.format(project._id)
        res = self.app.put_json(url, {
            'title': new_title,
            'public': True,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
        new_title = 'An <script>alert("even cooler")</script> project'
        project = self.project = ProjectFactory(
            title=self.title, is_folder=True, is_public=True, creator=self.user)

        url = '/v2/collections/{}/'.format(project._id)
        res = self.app.patch_json(url, {
            'title': new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], strip_html(new_title))

    def test_writing_to_public_field(self):
        title = "Cool project"
        project = self.project = ProjectFactory(
            title=title, is_folder=True, is_public=True, creator=self.user)
        # Test non-contrib writing to public field
        url = '/v2/collections/{}/'.format(project._id)
        res = self.app.patch_json(url, {
            'is_public': False,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)
        # Test creator writing to public field (supposed to be read-only)
        res = self.app.patch_json(url, {
            'is_public': False,
        }, auth=self.basic_auth, expect_errors=True)
        # TODO: Figure out why the validator isn't raising when attempting to write to a read-only field
        # assert_equal(res.status_code, 403)

    def test_partial_update_public_project_logged_out(self):
        res = self.app.patch_json(self.public_url, {'title': self.new_title}, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_partial_update_public_project_logged_in(self):
        res = self.app.patch_json(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

        # Public resource, logged in, unauthorized
        res = self.app.patch_json(self.public_url, {
            'title': self.new_title,
        }, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_partial_update_private_project_logged_out(self):
        res = self.app.patch_json(self.private_url, {'title': self.new_title}, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_partial_update_private_project_logged_in_contributor(self):
        res = self.app.patch_json(self.private_url, {'title': self.new_title}, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['title'], self.new_title)

    def test_partial_update_private_project_logged_in_non_contributor(self):
        res = self.app.patch_json(self.private_url, {'title': self.new_title}, auth=self.basic_auth_two,
                                  expect_errors=True)
        assert_equal(res.status_code, 403)

class TestCollectionChildrenList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)
        self.project = ProjectFactory()
        self.project.add_contributor(self.user, permissions=['read', 'write'])
        self.project.save()
        self.component = NodeFactory(parent=self.project, creator=self.user, is_folder=True)
        self.pointer = ProjectFactory()
        self.project.add_pointer(self.pointer, auth=Auth(self.user), save=True)
        self.private_project_url = '/v2/collections/{}/children/'.format(self.project._id)

        self.public_project = ProjectFactory(is_folder=True, is_public=True, creator=self.user)
        self.public_project.save()
        self.public_component = NodeFactory(parent=self.public_project, is_folder=True, creator=self.user,
                                            is_public=True)
        self.public_project_url = '/v2/collections/{}/children/'.format(self.public_project._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

    def test_collection_children_list_does_not_include_pointers(self):
        res = self.app.get(self.private_project_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)

    def test_return_public_collection_children_list_logged_out(self):
        res = self.app.get(self.public_project_url)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_public_collection_children_list_logged_in(self):
        res = self.app.get(self.public_project_url, auth=self.basic_auth_two)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_component._id)

    def test_return_private_collection_children_list_logged_out(self):
        res = self.app.get(self.private_project_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_return_private_collection_children_list_logged_in_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.component._id)

    def test_return_private_collection_children_list_logged_in_non_contributor(self):
        res = self.app.get(self.private_project_url, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_collection_children_list_does_not_include_unauthorized_projects(self):
        private_component = NodeFactory(parent=self.project)
        res = self.app.get(self.private_project_url, auth=self.basic_auth)
        assert_equal(len(res.json['data']), 1)

        Node.remove()

class TestCollectionPointersList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))
        self.private_url = '/v2/collections/{}/pointers/'.format(self.project._id)

        self.public_folder = ProjectFactory(is_folder=True, is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_folder=True, is_public=True, creator=self.user)
        self.public_folder.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_url = '/v2/collections/{}/pointers/'.format(self.public_folder._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

    def test_return_public_collection_pointers_logged_out(self):
        res = self.app.get(self.public_url)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_public_collection_pointers_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth_two)
        res_json = res.json['data']
        assert_equal(len(res_json), 1)
        assert_equal(res.status_code, 200)
        assert_in(res_json[0]['node_id'], self.public_pointer_project._id)

    def test_return_private_collection_pointers_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

class TestCreateCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.pointer_project = ProjectFactory(is_public=False, creator=self.user)
        self.project.add_pointer(self.pointer_project, auth=Auth(self.user))
        self.private_url = '/v2/collections/{}/pointers/'.format(self.project._id)
        self.private_payload = {'node_id': self.project._id}

        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user))
        self.public_url = '/v2/collections/{}/pointers/'.format(self.public_project._id)
        self.public_payload = {'node_id': self.public_project._id}

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

    def test_creates_public_collection_pointer_logged_out(self):
        res = self.app.post(self.public_url, self.public_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_creates_public_collection_pointer_logged_in(self):
        res = self.app.post(self.public_url, self.public_payload, auth=self.basic_auth_two, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.post(self.public_url, self.public_payload, auth=self.basic_auth, expect_errors=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['node_id'], self.public_project._id)

    def test_creates_private_collection_pointer_logged_out(self):
        res = self.app.post(self.private_url, self.private_payload, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

class TestCollectionPointerDetail(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.private_project = ProjectFactory(creator=self.user, is_folder=True, is_public=False)
        self.pointer_project = ProjectFactory(creator=self.user, is_folder=True, is_public=False)
        self.pointer = self.private_project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/v2/collections/{}/pointers/{}'.format(self.private_project._id, self.pointer._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.public_project = ProjectFactory(is_public=True)
        self.public_pointer_project = ProjectFactory(is_public=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/v2/collections/{}/pointers/{}'.format(self.public_project._id, self.public_pointer._id)

    def test_returns_public_collection_pointer_detail_logged_out(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        res_json = res.json['data']
        assert_equal(res_json['node_id'], self.public_pointer_project._id)

    def test_returns_public_collection_pointer_detail_logged_in(self):
        res = self.app.get(self.public_url, auth=self.basic_auth)
        res_json = res.json['data']
        assert_equal(res.status_code, 200)
        assert_equal(res_json['node_id'], self.public_pointer_project._id)

    def test_returns_private_collection_pointer_detail_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

class TestDeleteCollectionPointer(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('password')
        self.user.save()
        self.basic_auth = (self.user.username, 'password')
        self.project = ProjectFactory(creator=self.user, is_public=False, is_folder=True)
        self.pointer_project = ProjectFactory(creator=self.user, is_public=True, is_folder=True)
        self.pointer = self.project.add_pointer(self.pointer_project, auth=Auth(self.user), save=True)
        self.private_url = '/v2/collections/{}/pointers/{}'.format(self.project._id, self.pointer._id)

        self.user_two = UserFactory.build()
        self.user_two.set_password('password')
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, 'password')

        self.public_project = ProjectFactory(is_public=True, creator=self.user, is_folder=True)
        self.public_pointer_project = ProjectFactory(is_public=True, creator=self.user, is_folder=True)
        self.public_pointer = self.public_project.add_pointer(self.public_pointer_project, auth=Auth(self.user),
                                                              save=True)
        self.public_url = '/v2/collections/{}/pointers/{}'.format(self.public_project._id, self.public_pointer._id)

    def test_deletes_public_collection_pointer_logged_out(self):
        res = self.app.delete(self.public_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_deletes_public_collection_pointer_logged_in(self):
        res = self.app.delete(self.public_url, auth=self.basic_auth_two, expect_errors=True)
        node_count_before = len(self.public_project.nodes_pointer)
        # This is could arguably be a 405, but we don't need to go crazy with status codes
        assert_equal(res.status_code, 403)
        assert_equal(node_count_before, len(self.public_project.nodes_pointer))

        res = self.app.delete(self.public_url, auth=self.basic_auth)
        assert_equal(res.status_code, 204)
        assert_equal(node_count_before - 1, len(self.public_project.nodes_pointer))

    def test_deletes_private_collection_pointer_logged_out(self):
        res = self.app.delete(self.private_url, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)
