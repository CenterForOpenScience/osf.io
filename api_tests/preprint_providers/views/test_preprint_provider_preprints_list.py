from nose.tools import *  # flake8: noqa
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)
from tests.base import ApiTestCase

class TestPreprintProviderPreprintsListFiltering(PreprintsListFilteringMixin):

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory(name='Sockarxiv')

    @pytest.fixture()
    def provider_two(self, provider_one):
        return provider_one

    @pytest.fixture()
    def provider_three(self, provider_one):
        return provider_one

    @pytest.fixture()
    def project_one(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def project_two(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def project_three(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url(self, provider_one):
        return '/{}preprint_providers/{}/preprints/?version=2.2&'.format(API_BASE, provider_one._id)

    def test_provider_filter_equals_returns_multiple(self, app, user, provider_one, preprint_one, preprint_two, preprint_three, provider_url):
        expected = set([preprint_one._id, preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(provider_url, provider_one._id), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

class TestPreprintProviderPreprintIsPublishedList(PreprintIsPublishedListMixin, ApiTestCase):

    def setUp(self):
        self.admin = AuthUserFactory()
        self.provider_one = PreprintProviderFactory()
        self.provider_two = self.provider_one
        self.published_project = ProjectFactory(creator=self.admin, is_public=True)
        self.public_project = ProjectFactory(creator=self.admin, is_public=True)
        self.url = '/{}preprint_providers/{}/preprints/?version=2.2&'.format(API_BASE, self.provider_one._id)
        super(TestPreprintProviderPreprintIsPublishedList, self).setUp()

class TestPreprintProviderPreprintIsValidList(PreprintIsValidListMixin):
    @pytest.fixture(autouse=True)
    def setUp(self):
        self.admin = AuthUserFactory()
        self.project = ProjectFactory(creator=self.admin, is_public=True)
        self.provider = PreprintProviderFactory()
        self.url = '/{}preprint_providers/{}/preprints/?version=2.2&'.format(API_BASE, self.provider._id)
        super(TestPreprintProviderPreprintIsValidList, self).setUp()
