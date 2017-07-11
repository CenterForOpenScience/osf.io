import pytest

from addons.osfstorage.models import OsfStorageFile
from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin
from framework.auth.core import Auth
from osf.models import PreprintService
from osf_tests.factories import (
    PreprintFactory, 
    AuthUserFactory, 
    ProjectFactory, 
    SubjectFactory, 
    PreprintProviderFactory,
)
from tests.base import ApiTestCase

class TestNodePreprintsListFiltering(PreprintsListFilteringMixin):

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory(name='Sockarxiv')

    @pytest.fixture()
    def provider_two(self):
        return PreprintProviderFactory(name='Piratearxiv')

    @pytest.fixture()
    def provider_three(self):
        return PreprintProviderFactory(name='Mockarxiv')

    @pytest.fixture()
    def project_one(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def project_two(self, project_one):
        return project_one

    @pytest.fixture()
    def project_three(self, project_one):
        return project_one

    @pytest.fixture()
    def url(self, project_one):
        return '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, project_one._id)

    def test_provider_filter_equals_returns_one(self, app, user, provider_two, preprint_two, provider_url):
        expected = [preprint_two._id]
        res = app.get('{}{}'.format(provider_url, provider_two._id), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

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
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.admin = AuthUserFactory()
        self.project = ProjectFactory(creator=self.admin, is_public=True)
        self.provider = PreprintProviderFactory()
        self.url = '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, self.project._id)
        super(TestNodePreprintIsValidList, self).setUp()

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
