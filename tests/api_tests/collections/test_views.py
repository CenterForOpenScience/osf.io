# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from website.models import Node
from website.util.sanitize import strip_html

from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, RegistrationFactory, DashboardFactory, \
    NodeFactory


class TestWelcomeToApi(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        self.user.set_password('justapoorboy')
        self.user.save()
        self.basic_auth = (self.user.username, 'justapoorboy')
        self.url = '/v2/'

    def test_returns_200_for_logged_out_user(self):
        res = self.app.get(self.url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['current_user'], None)

    def test_returns_current_user_info_when_logged_in(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['meta']['current_user']['data']['given_name'], self.user.given_name)


class TestNodeList(ApiTestCase):
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

    def test_return_private_node_list_logged_out_user(self):
        res = self.app.get(self.url)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_contributor(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_in(self.private._id, ids)

    def test_return_private_node_list_logged_in_non_contributor(self):
        res = self.app.get(self.url, auth=self.basic_non_contrib_auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.public._id, ids)
        assert_not_in(self.private._id, ids)

        Node.remove()


