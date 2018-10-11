import pytest

from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin
from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    PreprintProviderFactory,
)
from django.utils import timezone
from osf.utils import permissions


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
        return ProjectFactory(
            title='Public Project User One',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def project_private(self, user_one):
        return ProjectFactory(
            title='Private Project User One',
            is_public=False,
            creator=user_one)

    def test_gets(
            self, app, user_one, user_two, preprint,
            project_public, project_private):

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

        abandoned_preprint = PreprintFactory(creator=user_one, finish=False)
        abandoned_preprint.machine_state = 'initial'
        abandoned_preprint.save()
        url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        actual = [result['id'] for result in res.json['data']]
        assert abandoned_preprint._id not in actual


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

    def test_provider_filter_equals_returns_one(
            self, app, user, provider_two, preprint_two, provider_url):
        expected = [preprint_two._id]
        res = app.get(
            '{}{}'.format(
                provider_url,
                provider_two._id),
            auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_filter_withdrawn_preprint(self, app, url, user):
        preprint_one = PreprintFactory(is_published=False, creator=user)
        preprint_one.date_withdrawn = timezone.now()
        preprint_one.is_public = True
        preprint_one.is_published = True
        preprint_one.date_published = timezone.now()
        preprint_one.machine_state = 'accepted'
        assert preprint_one.ever_public is False
        # Putting this preprint in a weird state, is verified_publishable, but has been
        # withdrawn and ever_public is False.  This is to isolate withdrawal portion of query
        preprint_one.save()

        preprint_two = PreprintFactory(creator=user)
        preprint_two.date_withdrawn = timezone.now()
        preprint_two.ever_public = True
        preprint_two.save()

        # Unauthenticated users cannot see users/me/preprints
        url = '/{}users/me/preprints/?version=2.2&'.format(API_BASE)
        expected = [preprint_two._id]
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # Noncontribs cannot see withdrawn preprints
        user2 = AuthUserFactory()
        url = '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, user2._id)
        expected = []
        res = app.get(url, auth=user2.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert set(expected) == set(actual)

        # Read contribs - contrib=False on UserPreprints filter so read contribs can only see
        # withdrawn preprints that were once public
        user2 = AuthUserFactory()
        preprint_one.add_contributor(user2, 'read', save=True)
        preprint_two.add_contributor(user2, 'read', save=True)
        url = '/{}users/{}/preprints/?version=2.2&'.format(API_BASE, user2._id)
        expected = [preprint_two._id]
        res = app.get(url, auth=user2.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert set(expected) == set(actual)

        expected = [preprint_two._id]
        # Admin contribs can only see withdrawn preprints that were once public
        res = app.get(url, auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert set(expected) == set(actual)


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
        project_public = ProjectFactory(
            creator=user_admin_contrib, is_public=True)
        project_public.add_contributor(
            user_write_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True)
        return project_public

    @pytest.fixture()
    def url(self, user_admin_contrib):
        return '/{}users/{}/preprints/?version=2.2&'.format(
            API_BASE, user_admin_contrib._id)

    @pytest.fixture()
    def preprint_unpublished(
            self, user_admin_contrib, provider_one,
            project_public, subject):
        return PreprintFactory(
            creator=user_admin_contrib,
            filename='mgla.pdf',
            provider=provider_one,
            subjects=[[subject._id]],
            project=project_public,
            is_published=False)

    def test_unpublished_invisible_to_admins(
            self, app, user_admin_contrib, preprint_unpublished,
            preprint_published, url):
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_write_contribs(
            self, app, user_write_contrib, preprint_unpublished,
            preprint_published, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [
            d['id'] for d in res.json['data']]

    def test_filter_published_false_write_contrib(
            self, app, user_write_contrib, preprint_unpublished, url):
        res = app.get(
            '{}filter[is_published]=false'.format(url),
            auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0

    def test_filter_published_false_admin(
            self, app, user_admin_contrib, preprint_unpublished, url):
        res = app.get(
            '{}filter[is_published]=false'.format(url),
            auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 0
        assert preprint_unpublished._id not in [d['id'] for d in res.json['data']]


class TestUserPreprintIsValidList(PreprintIsValidListMixin):

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user_admin_contrib, user_write_contrib):
        project = ProjectFactory(creator=user_admin_contrib, is_public=True)
        project.add_contributor(
            user_write_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True)
        return project

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def url(self, user_admin_contrib):
        return '/{}users/{}/preprints/?version=2.2&'.format(
            API_BASE, user_admin_contrib._id)

    # test override: user nodes/preprints routes do not show private preprints to
    # anyone but the self
    def test_preprint_private_visible_write(
            self, app, user_write_contrib, project, preprint, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        preprint.is_public = False
        preprint.save()
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0

    # test override: user preprints routes do not show orphaned preprints to
    # anyone but the self
    def test_preprint_is_preprint_orphan_visible_write(
            self, app, project, preprint, url, user_write_contrib):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        preprint.primary_file = None
        preprint.save()
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0

    # test override, abandoned don't show up for anyone under UserPreprints
    def test_preprint_has_abandoned_preprint(
            self, app, user_admin_contrib, user_write_contrib, user_non_contrib,
            preprint, url):
        preprint.machine_state = 'initial'
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
