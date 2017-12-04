import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
)
from website.util import permissions

@pytest.mark.django_db
class PreprintListMatchesPreprintDetailMixin:

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin_contrib(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_published(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_public(self):
        raise NotImplementedError

    @pytest.fixture()
    def list_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def detail_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def file_project_public(self, user_admin_contrib, project_public):
        return test_utils.create_test_file(project_public, user_admin_contrib, 'mgla.pdf')

    @pytest.fixture()
    def file_project_published(self, user_admin_contrib, project_published):
        return test_utils.create_test_file(project_published, user_admin_contrib, 'saor.pdf')

    @pytest.fixture()
    def preprint_unpublished(self, user_admin_contrib, provider_one, project_public, subject):
        raise NotImplementedError

    @pytest.fixture()
    def preprint_published(self, user_admin_contrib, provider_two, project_published, subject):
        return PreprintFactory(creator=user_admin_contrib, filename='saor.pdf', provider=provider_two, subjects=[[subject._id]], project=project_published, is_published=True)

    def test_unpublished_invisible_to_non_contribs(self, app, user_non_contrib, preprint_unpublished, preprint_published, list_url, detail_url):
        res = app.get(list_url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

        res = app.get(detail_url, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_unpublished_invisible_to_public(self, app, preprint_unpublished, preprint_published, list_url, detail_url):
        res = app.get(list_url)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

        res = app.get(detail_url, expect_errors=True)
        assert res.status_code == 401


@pytest.mark.django_db
class PreprintIsPublishedListMixin:

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_admin_contrib(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_published(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_public(self):
        raise NotImplementedError

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def file_project_public(self, user_admin_contrib, project_public):
        return test_utils.create_test_file(project_public, user_admin_contrib, 'mgla.pdf')

    @pytest.fixture()
    def file_project_published(self, user_admin_contrib, project_published):
        return test_utils.create_test_file(project_published, user_admin_contrib, 'saor.pdf')

    @pytest.fixture()
    def preprint_unpublished(self, user_admin_contrib, provider_one, project_public, subject):
        raise NotImplementedError

    @pytest.fixture()
    def preprint_published(self, user_admin_contrib, provider_two, project_published, subject):
        return PreprintFactory(creator=user_admin_contrib, filename='saor.pdf', provider=provider_two, subjects=[[subject._id]], project=project_published, is_published=True)

    def test_unpublished_invisible_to_non_contribs(self, app, user_non_contrib, preprint_unpublished, preprint_published, url):
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_public(self, app, preprint_unpublished, preprint_published, url):
        res = app.get(url)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

    def test_filter_published_false_non_contrib(self, app, user_non_contrib, url):
        res = app.get('{}filter[is_published]=false'.format(url), auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_public(self, app, url):
        res = app.get('{}filter[is_published]=false'.format(url))
        assert len(res.json['data']) == 0

    def test_filter_published_false_admin(self, app, user_admin_contrib, preprint_unpublished, preprint_published, url):
        res = app.get('{}filter[is_published]=false'.format(url), auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id in [d['id'] for d in res.json['data']]


@pytest.mark.django_db
class PreprintIsValidListMixin:

    @pytest.fixture()
    def user_admin_contrib(self):
        raise NotImplementedError

    @pytest.fixture()
    def project(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self):
        raise NotImplementedError

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def file_project(self, user_admin_contrib, project):
        return test_utils.create_test_file(project, user_admin_contrib, 'saor.pdf')

    @pytest.fixture()
    def preprint(self, user_admin_contrib, project, provider, subject):
        return PreprintFactory(creator=user_admin_contrib, filename='saor.pdf', provider=provider, subjects=[[subject._id]], project=project, is_published=True)

    def test_preprint_private_invisible_no_auth(self, app, project, preprint, url):
        res = app.get(url)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url)
        assert len(res.json['data']) == 0

    def test_preprint_private_invisible_non_contributor(self, app, user_non_contrib, project, preprint, url):
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0

    def test_preprint_private_visible_write(self, app, user_write_contrib, project, preprint, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1

    def test_preprint_private_visible_owner(self, app, user_admin_contrib, project, preprint, url):
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 1

    def test_preprint_node_deleted_invisible(self, app, user_admin_contrib, user_write_contrib, user_non_contrib, project, preprint, url):
        project.is_deleted = True
        project.save()
        # unauth
        res = app.get(url)
        assert len(res.json['data']) == 0
        # non_contrib
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 0

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_preprint_node_null_invisible(self, mock_preprint_updated, app, user_admin_contrib, user_write_contrib, user_non_contrib, preprint, url):
        preprint.node = None
        preprint.save()

        # unauth
        res = app.get(url)
        assert len(res.json['data']) == 0
        # non_contrib
        res = app.get(url, auth=user_non_contrib.auth)
        assert len(res.json['data']) == 0
        # write_contrib
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0
        # admin
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 0

        assert mock_preprint_updated.called