# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from osf_tests.factories import AuthUserFactory, PreprintFactory, ProjectFactory

from api.base.settings.defaults import API_BASE


class TestUserPreprints(ApiTestCase):

    def setUp(self):
        super(TestUserPreprints, self).setUp()
        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.preprint = PreprintFactory(title="Preprint User One", creator=self.user_one)
        self.public_project = ProjectFactory(title="Public Project User One", is_public=True, creator=self.user_one)
        self.private_project = ProjectFactory(title="Private Project User One", is_public=False, creator=self.user_one)

    def tearDown(self):
        super(TestUserPreprints, self).tearDown()

    def test_authorized_in_gets_200(self):
        url = "/{}users/{}/preprints/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.user_one.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_anonymous_gets_200(self):
        url = "/{}users/{}/preprints/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_get_preprints_logged_in(self):
        url = "/{}users/{}/preprints/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.private_project._id, ids)

    def test_get_projects_not_logged_in(self):
        url = "/{}users/{}/preprints/".format(API_BASE, self.user_one._id)
        res = self.app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.private_project._id, ids)

    def test_get_projects_logged_in_as_different_user(self):
        url = "/{}users/{}/preprints/".format(API_BASE, self.user_one._id)
        res = self.app.get(url, auth=self.user_two.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.public_project._id, ids)
        assert_not_in(self.private_project._id, ids)

