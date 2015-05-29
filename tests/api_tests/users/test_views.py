# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, DashboardFactory


class TestUsers(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.save()
        self.user_two = UserFactory.build()
        self.user_two.save()

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_returns_200(self):
        res = self.app.get('/v2/users/')
        assert_equal(res.status_code, 200)

    def test_find_user_in_users(self):
        url = "/v2/users/"

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_two._id, ids)

    def test_all_users_in_users(self):
        url = "/v2/users/"

        res = self.app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_multiple_in_users(self):
        url = "/v2/users/?filter[fullname]=fred"

        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_in(self.user_two._id, ids)

    def test_find_single_user_in_users(self):
        url = "/v2/users/?filter[fullname]=my"
        self.user_one.fullname = 'My Mom'
        self.user_one.save()
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)

    def test_find_no_user_in_users(self):
        url = "/v2/users/?filter[fullname]=NotMyMom"
        res = self.app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert_not_in(self.user_one._id, ids)
        assert_not_in(self.user_two._id, ids)


class TestUserDetail(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')

    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_gets_200(self):
        url = "/v2/users/{}/".format(self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_correct_pk_user(self):
        url = "/v2/users/{}/".format(self.user_one._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['social_accounts']['twitter'], 'howtopizza')

    def test_get_incorrect_pk_user_logged_in(self):
        url = "/v2/users/{}/".format(self.user_two._id)
        res = self.app.get(url)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)

    def test_get_incorrect_pk_user_not_logged_in(self):
        url = "/v2/users/{}/".format(self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        user_json = res.json['data']
        assert_not_equal(user_json['fullname'], self.user_one.fullname)
        assert_equal(user_json['fullname'], self.user_two.fullname)


class TestUserNodes(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.user_one_url = '/v2/users/{}/'.format(self.user_one._id)
        self.user_two_url = '/v2/users/{}/'.format(self.user_two._id)
        self.public_project_user_one = ProjectFactory(title="Public Project User One", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two", is_public=True, creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False, creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.dashboard = DashboardFactory()


    def tearDown(self):
        ApiTestCase.tearDown(self)
        Node.remove()

    def test_authorized_in_gets_200(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        assert_equal(res.status_code, 200)

    def test_anonymous_gets_200(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_get_projects_logged_in(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_not_logged_in(self):
        url = "/v2/users/{}/nodes/".format(self.user_one._id)
        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.public_project_user_two._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)

    def test_get_projects_logged_in_as_different_user(self):
        url = "/v2/users/{}/nodes/".format(self.user_two._id)
        res = self.app.get(url, auth=self.auth_one)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.public_project_user_two._id, ids)
        assert_not_in(self.public_project_user_one._id, ids)
        assert_not_in(self.private_project_user_one._id, ids)
        assert_not_in(self.private_project_user_two._id, ids)
        assert_not_in(self.folder._id, ids)
        assert_not_in(self.deleted_project_user_one._id, ids)


class TestUserUpdate(ApiTestCase):

    def setUp(self):
        ApiTestCase.setUp(self)
        self.user_one = UserFactory.build()
        self.user_one.set_password('justapoorboy')
        self.user_one.social['twitter'] = 'howtopizza'
        self.user_one.fullname = 'My Full Name'
        self.user_one.save()
        self.auth_one = (self.user_one.username, 'justapoorboy')
        self.user_two = UserFactory.build()
        self.user_two.set_password('justapoorboy')
        self.user_two.save()
        self.auth_two = (self.user_two.username, 'justapoorboy')
        self.twitter = 'hotcrossbuns'
        self.new_twitter = 'yourmom'
        self.new_name = 'Flash Gordon'
        self.public_project_user_one = ProjectFactory(title="Public Project User One", is_public=True, creator=self.user_one)
        self.private_project_user_one = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)
        self.public_project_user_two = ProjectFactory(title="Public Project User Two", is_public=True, creator=self.user_two)
        self.private_project_user_two = ProjectFactory(title="Private Project User Two", is_public=False, creator=self.user_two)
        self.deleted_project_user_one = FolderFactory(title="Deleted Project User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.folder = FolderFactory()
        self.deleted_folder = FolderFactory(title="Deleted Folder User One", is_public=False, creator=self.user_one, is_deleted=True)
        self.dashboard = DashboardFactory()
        self.user_one_url = "/v2/users/{}/".format(self.user_one._id)
        self.user_two_url = "/v2/users/{}/".format(self.user_two._id)

    def test_user_logged_out(self):
        res = self.app.put_json(self.user_one_url, {
            'fullname': self.new_name,
        }, expect_errors=True)
        # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
        # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
        # a little better
        assert_equal(res.status_code, 403)

    def test_update_user_logged_in(self):
        # Logged in User updates his own stuff
        res = self.app.put_json(self.user_one_url, {
            'fullname': self.new_name
        }, auth=self.auth_one)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['fullname'], self.new_name)

    #
    # def test_update_private_project_logged_out(self):
    #     res = self.app.put_json(self.private_url, {
    #         'title': self.new_title,
    #         'description': self.new_description,
    #         'category': self.new_category,
    #         'public': False,
    #     }, expect_errors=True)
    #     # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
    #     # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
    #     # a little better
    #     assert_equal(res.status_code, 403)
    #
    # def test_update_private_project_logged_in_contributor(self):
    #     res = self.app.put_json(self.private_url, {
    #         'title': self.new_title,
    #         'description': self.new_description,
    #         'category': self.new_category,
    #         'public': False,
    #     }, auth=self.basic_auth)
    #     assert_equal(res.status_code, 200)
    #     assert_equal(res.json['data']['title'], self.new_title)
    #     assert_equal(res.json['data']['description'], self.new_description)
    #     assert_equal(res.json['data']['category'], self.new_category)
    #
    # def test_update_private_project_logged_in_non_contributor(self):
    #     res = self.app.put_json(self.private_url, {
    #         'title': self.new_title,
    #         'description': self.new_description,
    #         'category': self.new_category,
    #         'public': False,
    #     }, auth=self.basic_auth_two, expect_errors=True)
    #     assert_equal(res.status_code, 403)
    #
    # def test_update_project_sanitizes_html_properly(self):
    #     """Post request should update resource, and any HTML in fields should be stripped"""
    #     new_title = '<strong>Super</strong> Cool Project'
    #     new_description = 'An <script>alert("even cooler")</script> project'
    #     project = self.project = ProjectFactory(
    #         title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)
    #
    #     url = '/v2/users/{}/'.format(project._id)
    #     res = self.app.put_json(url, {
    #         'title': new_title,
    #         'description': new_description,
    #         'category': self.new_category,
    #         'public': True,
    #     }, auth=self.basic_auth)
    #     assert_equal(res.status_code, 200)
    #     assert_equal(res.json['data']['title'], strip_html(new_title))
    #     assert_equal(res.json['data']['description'], strip_html(new_description))
    #
    # def test_partial_update_project_updates_project_correctly_and_sanitizes_html(self):
    #     new_title = 'An <script>alert("even cooler")</script> project'
    #     project = self.project = ProjectFactory(
    #         title=self.title, description=self.description, category=self.category, is_public=True, creator=self.user)
    #
    #     url = '/v2/users/{}/'.format(project._id)
    #     res = self.app.patch_json(url, {
    #         'title': new_title,
    #     }, auth=self.basic_auth)
    #     assert_equal(res.status_code, 200)
    #     res = self.app.get(url)
    #     assert_equal(res.status_code, 200)
    #     assert_equal(res.json['data']['title'], strip_html(new_title))
    #     assert_equal(res.json['data']['description'], self.description)
    #     assert_equal(res.json['data']['category'], self.category)
    #
    # def test_writing_to_public_field(self):
    #     title = "Cool project"
    #     description = 'A Properly Cool Project'
    #     category = 'data'
    #     project = self.project = ProjectFactory(
    #         title=title, description=description, category=category, is_public=True, creator=self.user)
    #     # Test non-contrib writing to public field
    #     url = '/v2/users/{}/'.format(project._id)
    #     res = self.app.patch_json(url, {
    #         'is_public': False,
    #     }, auth=self.basic_auth_two, expect_errors=True)
    #     assert_equal(res.status_code, 403)
    #     # Test creator writing to public field (supposed to be read-only)
    #     res = self.app.patch_json(url, {
    #         'is_public': False,
    #     }, auth=self.basic_auth, expect_errors=True)
    #     assert_true(res.json['data']['public'])
    #     # TODO: Figure out why the validator isn't raising when attempting to write to a read-only field
    #     # assert_equal(res.status_code, 403)
    #
    # def test_partial_update_public_project_logged_out(self):
    #     res = self.app.patch_json(self.public_url, {'title': self.new_title}, expect_errors=True)
    #     # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
    #     # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
    #     # a little better
    #     assert_equal(res.status_code, 403)
    #
    # def test_partial_update_public_project_logged_in(self):
    #     res = self.app.patch_json(self.public_url, {
    #         'title': self.new_title,
    #     }, auth=self.basic_auth)
    #     assert_equal(res.status_code, 200)
    #     assert_equal(res.json['data']['title'], self.new_title)
    #     assert_equal(res.json['data']['description'], self.description)
    #     assert_equal(res.json['data']['category'], self.category)
    #
    #     # Public resource, logged in, unauthorized
    #     res = self.app.patch_json(self.public_url, {
    #         'title': self.new_title,
    #     }, auth=self.basic_auth_two, expect_errors=True)
    #     assert_equal(res.status_code, 403)
    #
    # def test_partial_update_private_project_logged_out(self):
    #     res = self.app.patch_json(self.private_url, {'title': self.new_title}, expect_errors=True)
    #     # This is 403 instead of 401 because basic authentication is only for unit tests and, in order to keep from
    #     # presenting a basic authentication dialog box in the front end. We may change this as we understand CAS
    #     # a little better
    #     assert_equal(res.status_code, 403)
    #
    # def test_partial_update_private_project_logged_in_contributor(self):
    #     res = self.app.patch_json(self.private_url, {'title': self.new_title}, auth=self.basic_auth)
    #     assert_equal(res.status_code, 200)
    #     assert_equal(res.json['data']['title'], self.new_title)
    #     assert_equal(res.json['data']['description'], self.description)
    #     assert_equal(res.json['data']['category'], self.category)
    #
    # def test_partial_update_private_project_logged_in_non_contributor(self):
    #     res = self.app.patch_json(self.private_url, {'title': self.new_title}, auth=self.basic_auth_two, expect_errors=True)
    #     assert_equal(res.status_code, 403)
    #
