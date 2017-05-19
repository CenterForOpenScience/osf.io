import pytest

from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.json_api_test_app import JSONAPITestApp
from website.util import permissions
from api_tests import utils as test_utils
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
)

class PreprintIsPublishedListMixin(object):

    def setUp(self):
        super(PreprintIsPublishedListMixin, self).setUp()
        assert self.admin, 'Subclasses of PreprintIsPublishedMixin must define self.admin'
        assert self.provider_one, 'Subclasses of PreprintIsPublishedMixin must define self.provider_one'
        assert self.provider_two, 'Subclasses of PreprintIsPublishedMixin must define self.provider_two'
        assert self.published_project, 'Subclasses of PreprintIsPublishedMixin must define self.published_project'
        assert self.public_project, 'Subclasses of PreprintIsPublishedMixin must define self.public_project'
        assert self.url, 'Subclasses of PreprintIsPublishedMixin must define self.url'

        self.write_contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()

        self.public_project.add_contributor(self.write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        self.subject = SubjectFactory()

        self.file_one_public_project = test_utils.create_test_file(self.public_project, self.admin, 'mgla.pdf')
        self.file_one_published_project = test_utils.create_test_file(self.published_project, self.admin, 'saor.pdf')

        self.unpublished_preprint = PreprintFactory(creator=self.admin, filename='mgla.pdf', provider=self.provider_one, subjects=[[self.subject._id]], project=self.public_project, is_published=False)
        self.published_preprint = PreprintFactory(creator=self.admin, filename='saor.pdf', provider=self.provider_two, subjects=[[self.subject._id]], project=self.published_project, is_published=True)

    def test_unpublished_visible_to_admins(self):
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 2
        assert self.unpublished_preprint._id in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_write_contribs(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_non_contribs(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_public(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id not in [d['id'] for d in res.json['data']]

    def test_filter_published_false_admin(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.admin.auth)
        assert len(res.json['data']) == 1
        assert self.unpublished_preprint._id in [d['id'] for d in res.json['data']]

    def test_filter_published_false_write_contrib(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.write_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_non_contrib(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url), auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_public(self):
        res = self.app.get('{}filter[is_published]=false'.format(self.url))
        assert len(res.json['data']) == 0

@pytest.mark.django_db
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
    def test_preprint_private_invisible_no_auth(self):
        res = self.app.get(self.url)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url)
        assert len(res.json['data']) == 0

    def test_preprint_private_invisible_non_contributor(self):
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_preprint_private_visible_write(self):
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.write_contrib.auth)
        assert len(res.json['data']) == 1

    def test_preprint_private_visible_owner(self):
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1
        self.project.is_public = False
        self.project.save()
        res = self.app.get(self.url, auth=self.admin.auth)
        assert len(res.json['data']) == 1

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
