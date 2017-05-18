import pytest
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin

from website.preprints.model import PreprintService
from website.files.models.osfstorage import OsfStorageFile
from osf_tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory, PreprintProviderFactory
from api_tests import utils as test_utils

class TestNodePreprintsListFiltering(PreprintsListFilteringMixin, ApiTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        # all different providers
        self.provider = PreprintProviderFactory(name='Sockarxiv')
        self.provider_two = PreprintProviderFactory(name='Piratearxiv')
        self.provider_three = PreprintProviderFactory(name='Mockarxiv')
        # all same project
        self.project = ProjectFactory(creator=self.user)
        self.project_two = self.project
        self.project_three = self.project
        self.url = '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, self.project._id)
        super(TestNodePreprintsListFiltering, self).setUp()

    def test_provider_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.provider_url, self.provider_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

class TestNodePreprintIsPublishedList(PreprintIsPublishedListMixin, ApiTestCase):
    def setUp(self):
        self.admin = AuthUserFactory()
        self.provider_one = PreprintProviderFactory()
        self.provider_two = PreprintProviderFactory()
        self.published_project = ProjectFactory(creator=self.admin, is_public=True)
        self.public_project = self.published_project
        self.url = '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, self.published_project._id)
        super(TestNodePreprintIsPublishedList, self).setUp()

class TestNodePreprintIsValidList(PreprintIsValidListMixin):
    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, admin):
        return ProjectFactory(creator=admin, is_public=True)

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, project._id)

    # test override: custom exception checks because of node permission failures
    def test_preprint_private_invisible_no_auth(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401

    # test override: custom exception checks because of node permission failures
    def test_preprint_private_invisible_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    # test override: custom exception checks because of node permission failures
    def test_preprint_node_deleted_invisible(self):
        self.project.is_deleted = True
        self.project.save()
        # no auth
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 410
        # contrib
        res = self.app.get(self.url, auth=self.non_contrib.auth, expect_errors=True)
        assert res.status_code == 410
        # write_contrib
        res = self.app.get(self.url, auth=self.write_contrib.auth, expect_errors=True)
        assert res.status_code == 410
        # admin
        res = self.app.get(self.url, auth=self.admin.auth, expect_errors=True)
        assert res.status_code == 410
