import pytest

from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin
from osf.models import PreprintService, Node
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory,
)
from website.util import permissions


@pytest.mark.django_db
class TestUserPreprints:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user_one):
        return PreprintFactory(title='Preprint User One', creator=user_one)

    @pytest.fixture()
    def project_public(self, user_one):
        return ProjectFactory(title='Public Project User One', is_public=True, creator=user_one)

    @pytest.fixture()
    def project_private(self, user_one):
        return ProjectFactory(title='Private Project User One', is_public=False, creator=user_one)

    def test_gets(self, app, user_one, user_two, preprint, project_public, project_private):

    #   test_authorized_in_gets_200
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_anonymous_gets_200
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_get_preprints_logged_in
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert preprint._id in ids
        assert project_public._id not in ids
        assert project_private._id not in ids

    #   test_get_projects_not_logged_in
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert preprint._id in ids
        assert project_public._id not in ids
        assert project_private._id not in ids

    #   test_get_projects_logged_in_as_different_user
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert preprint._id in ids
        assert project_public._id not in ids
        assert project_private._id not in ids


class TestUserPreprintsListFiltering(PreprintsListFilteringMixin):

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
    def url(self, user):
        return '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, user._id)

    def test_provider_filter_equals_returns_one(self, app, user, provider_two, preprint_two, provider_url):
        expected = [preprint_two._id]
        res = app.get('{}{}'.format(provider_url, provider_two._id), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual


class TestUserPreprintIsPublishedList(PreprintIsPublishedListMixin):

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider_two(self, provider_one):
        return provider_one

    @pytest.fixture()
    def project_published(self, user_admin_contrib):
        return ProjectFactory(creator=user_admin_contrib, is_public=True)

    @pytest.fixture()
    def project_public(self, user_admin_contrib, user_write_contrib):
        project_public = ProjectFactory(creator=user_admin_contrib, is_public=True)
        project_public.add_contributor(user_write_contrib, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project_public

    @pytest.fixture()
    def url(self, user_admin_contrib):
        return '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, user_admin_contrib._id)

    @pytest.fixture()
    def preprint_unpublished(self, user_admin_contrib, provider_one, project_public, subject):
        return PreprintFactory(creator=user_admin_contrib, filename='mgla.pdf', provider=provider_one, subjects=[[subject._id]], project=project_public, is_published=False)

    def test_unpublished_visible_to_admins(self, app, user_admin_contrib, preprint_unpublished, preprint_published, url):
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 2
        assert preprint_unpublished._id in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_write_contribs(self, app, user_write_contrib, preprint_unpublished, preprint_published, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

    def test_filter_published_false_write_contrib(self, app, user_write_contrib, preprint_unpublished, url):
        res = app.get('{}filter[is_published]=false'.format(url), auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0

class TestUserPreprintIsValidList(PreprintIsValidListMixin):

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
    def url(self, user_admin_contrib):
        return '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, user_admin_contrib._id)

    # test override: user nodes/preprints routes do not show private nodes to anyone but the self
    def test_preprint_private_visible_write(self, app, user_write_contrib, project, preprint, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        project.is_public = False
        project.save()
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0
