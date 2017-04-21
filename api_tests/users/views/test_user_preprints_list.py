# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)
from osf.models import PreprintService, Node

from website.util import permissions

from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin

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

class TestUserPreprintsListFiltering(PreprintsListFilteringMixin, ApiTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.provider = PreprintProviderFactory(name='Sockarxiv')
        self.provider_two = PreprintProviderFactory(name='Piratearxiv')
        self.provider_three = self.provider
        self.project = ProjectFactory(creator=self.user)
        self.project_two = ProjectFactory(creator=self.user)
        self.project_three = ProjectFactory(creator=self.user)
        self.url = '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, self.user._id)
        super(TestUserPreprintsListFiltering, self).setUp()

    def test_provider_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.provider_url, self.provider_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)


class TestUserPreprintIsPublishedList(PreprintIsPublishedListMixin, ApiTestCase):
    def setUp(self):
        self.admin = AuthUserFactory()
        self.provider_one = PreprintProviderFactory()
        self.provider_two = self.provider_one
        self.published_project = ProjectFactory(creator=self.admin, is_public=True)
        self.public_project = ProjectFactory(creator=self.admin, is_public=True)
        self.url = '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, self.admin._id)
        super(TestUserPreprintIsPublishedList, self).setUp()


class TestUserPreprintIsValidList(PreprintIsValidListMixin, ApiTestCase):
    def setUp(self):
        self.admin = AuthUserFactory()
        self.provider = PreprintProviderFactory()
        self.project = ProjectFactory(creator=self.admin, is_public=True)
        self.url = '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, self.admin._id)
        super(TestUserPreprintIsValidList, self).setUp()

    # User nodes/preprints routes do not show private nodes to anyone but the self
    def test_preprint_private_visible_write(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0
