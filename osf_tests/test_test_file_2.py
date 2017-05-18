import pytest
import unittest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
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

class TestFile:
    @pytest.fixture
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture
    def url(self):
        return '/{}preprints/?version=2.2&'.format(API_BASE)

    @pytest.fixture
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture
    def subject(self):
        return SubjectFactory()

    @pytest.fixture
    def project(self, admin, write_contrib):
        project = ProjectFactory(creator=admin, is_public=True)
        project.add_contributor(write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project

    @pytest.fixture
    def file_one_project(self, project, admin):
        return test_utils.create_test_file(project, admin, 'saor.pdf')

    @pytest.fixture
    def preprint(self, admin, provider, subject, project):
        return PreprintFactory(creator=admin, filename='saor.pdf', provider=provider, subjects=[[subject._id]], project=project, is_published=True)

    # Test private
    def test_preprint_private_invisible_no_auth(self, app, url, project, preprint):
        res = app.get(url)
        print app.get(url)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url)
        assert len(res.json['data']) == 0

    def test_preprint_private_invisible_non_contributor(self, app, url, non_contrib, project, preprint):
        res = app.get(url, auth=non_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_preprint_private_visible_write(self, app, url, write_contrib, project, preprint):
        res = app.get(url, auth=write_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=write_contrib.auth)
        assert len(res.json['data']) == 1

    def test_preprint_private_visible_owner(self, app, url, admin, project, preprint):
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 1

    def test_preprint_node_deleted_invisible(self, app, url, project, non_contrib, write_contrib, admin):
        project.is_deleted = True
        project.save()
        # no auth
        res = app.get(url)
        assert len(res.json['data']) == 0
        # contrib
        res = app.get(url, auth=non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = app.get(url, auth=write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 0

    def test_preprint_node_null_invisible(self, app, url, non_contrib, write_contrib, admin, project, preprint):
        preprint.node = None
        preprint.save()
        # no auth
        res = app.get(url)
        assert len(res.json['data']) == 0
        # contrib
        res = app.get(url, auth=non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = app.get(url, auth=write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = app.get(url, auth=admin.auth)
        assert len(res.json['data']) == 0
