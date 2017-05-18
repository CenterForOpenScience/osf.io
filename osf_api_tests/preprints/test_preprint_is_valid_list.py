import pytest

from api.base.settings.defaults import API_BASE
from osf_api_tests.mixins.preprint_is_valid_list_mixin import PreprintIsValidListMixin
from osf_api_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PreprintProviderFactory
)
from tests.json_api_test_app import JSONAPITestApp
from api_tests import utils as test_utils

pytestmark = pytest.mark.django_db

class TestPreprintUrl(PreprintIsValidListMixin):
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
    def url(self):
        return '/{}preprints/?version=2.2&'.format(API_BASE)

class TestPreprintProviderUrl(PreprintIsValidListMixin):
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
    def url(self, provider):
        return '/{}preprint_providers/{}/preprints/?version=2.2&'.format(API_BASE, provider._id)

class TestUserUrl(PreprintIsValidListMixin):
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
    def url(self, admin):
        return '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, admin._id)

    # test override: user nodes/preprints routes do not show private nodes to anyone but the self
    def preprint_private_visible_write(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0

class TestNodeUrl(PreprintIsValidListMixin):
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
    def preprint_private_invisible_no_auth(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, expect_errors=True)
        assert res.status_code == 401
        self.project.is_public = True
        self.project.save()

    # test override: custom exception checks because of node permission failures
    def preprint_private_invisible_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        self.project.is_public = True
        self.project.save()

    # test override: custom exception checks because of node permission failures
    def preprint_node_deleted_invisible(self):
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
        self.project.is_deleted = False
        self.project.save()
