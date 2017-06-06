import pytest

from api.base.settings.defaults import API_BASE
from osf_api_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    UserFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)
from tests.base import DbTestCase, ApiAppTestCase, SearchTestCase, MockRequestTestCase
from tests.json_api_test_app import JSONAPITestApp
from website.util import permissions
from api_tests import utils as test_utils

pytestmark = pytest.mark.django_db

class PreprintIsValidListMixin(object):

    # FIXTURES

    @pytest.fixture()
    def admin(self):
        raise NotImplementedError("subclass must define an admin fixture")

    @pytest.fixture()
    def url(self):
        raise NotImplementedError("subclass must define a url fixture")

    @pytest.fixture()
    def project(self, admin):
        raise NotImplementedError("subclass must define a project fixture")

    @pytest.fixture()
    def provider(self):
        raise NotImplementedError("subclass must define a provider")

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    # SETUP

    @pytest.fixture(scope="function", autouse=True)
    def int(self, app, url, admin, write_contrib, non_contrib, project, provider, subject):
        self.app = app
        self.url = url
        self.admin = admin
        self.write_contrib = write_contrib
        self.non_contrib = non_contrib
        self.project = project
        self.provider = provider
        self.subject = subject

        self.project.add_contributor(self.write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        test_utils.create_test_file(self.project, self.admin, 'saor.pdf')
        self.preprint = PreprintFactory(creator=self.admin, filename='saor.pdf', provider=self.provider, subjects=[[self.subject._id]], project=self.project, is_published=True)

    # TESTS

    @pytest.mark.group_test
    def test_preprint_is_valid_list(self):
        self.test_preprint_private_invisible_no_auth()
        self.test_preprint_private_invisible_non_contributor()
        self.test_preprint_private_visible_write()
        self.test_preprint_private_visible_owner()
        self.test_preprint_node_deleted_invisible()
        self.test_preprint_node_null_invisible()

    @pytest.mark.individual_test
    def test_preprint_private_invisible_no_auth(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0
        self.project.is_public = True
        self.project.save()

    @pytest.mark.individual_test
    def test_preprint_private_invisible_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0
        self.project.is_public = True
        self.project.save()

    @pytest.mark.individual_test
    def test_preprint_private_visible_write(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = True
        self.project.save()

    @pytest.mark.individual_test
    def test_preprint_private_visible_owner(self):
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = True
        self.project.save()

    @pytest.mark.individual_test
    def test_preprint_node_deleted_invisible(self):
        self.project.is_deleted = True
        self.project.save()
        # unauth
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0
        # non_contrib
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 0
        self.project.is_deleted = False
        self.project.save()

    @pytest.mark.individual_test
    def test_preprint_node_null_invisible(self):
        self.preprint.node = None
        self.preprint.save()
        # unauth
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0
        # non_contrib
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 0

