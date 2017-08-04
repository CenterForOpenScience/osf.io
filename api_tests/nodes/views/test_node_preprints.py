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
from website.util import permissions

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

class TestNodePreprintIsPublishedList(PreprintIsPublishedListMixin):

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider_two(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def project_published(self, user_admin_contrib):
        return ProjectFactory(creator=user_admin_contrib, is_public=True)

    @pytest.fixture()
    def project_public(self, user_write_contrib, project_published):
        project_published.add_contributor(user_write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project_published

    @pytest.fixture()
    def url(self, project_published):
        return '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, project_published._id)


class TestNodePreprintIsValidList(PreprintIsValidListMixin):

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user_admin_contrib, user_write_contrib):
        project = ProjectFactory(creator=user_admin_contrib, is_public=True)
        project.add_contributor(user_write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/preprints/?version=2.2&'.format(API_BASE, project._id)

    # test override: custom exception checks because of node permission failures
    def test_preprint_private_invisible_no_auth(self, app, project, preprint, url):
        res = app.get(url)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    # test override: custom exception checks because of node permission failures
    def test_preprint_private_invisible_non_contributor(self, app, user_non_contrib, project, preprint, url):
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    # test override: custom exception checks because of node permission failures
    def test_preprint_node_deleted_invisible(self, app, user_admin_contrib, user_write_contrib, user_non_contrib, project, preprint, url):
        project.is_deleted = True
        project.save()
        # no auth
        res = app.get(url, expect_errors=True)
        assert res.status_code == 410
        # contrib
        res = app.get(url, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 410
        # write_contrib
        res = app.get(url, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 410
        # admin
        res = app.get(url, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 410
