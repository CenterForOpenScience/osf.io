import pytest

from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from api_tests.preprints.views.test_preprint_list_mixin import PreprintIsPublishedListMixin, PreprintIsValidListMixin
from api_tests.reviews.mixins.filter_mixins import ReviewableFilterMixin

from osf_tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    PreprintProviderFactory,
)
from osf.utils import permissions


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
        return '/{}preprint_providers/{}/preprints/?version=2.2&'.format(
            API_BASE, provider_one._id)

    def test_provider_filter_equals_returns_multiple(
            self, app, user, provider_one, preprint_one,
            preprint_two, preprint_three, provider_url):
        expected = set(
            [preprint_one._id, preprint_two._id, preprint_three._id])
        res = app.get(
            '{}{}'.format(
                provider_url,
                provider_one._id),
            auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_reviews_state_counts(
            self, app, user, provider_one, preprint_one,
            preprint_two, preprint_three, url):
        url = '{}meta[reviews_state_counts]=true'.format(url)
        preprint_one.machine_state = 'pending'
        preprint_one.save()
        preprint_two.machine_state = 'pending'
        preprint_two.save()
        preprint_three.machine_state = 'accepted'
        preprint_three.save()

        expected = {
            'initial': 0,
            'pending': 2,
            'accepted': 1,
            'rejected': 0,
        }

        # non-moderators can't see counts
        res = app.get(url, auth=user.auth)
        assert 'reviews_state_counts' not in res.json['meta']

        provider_one.add_to_group(user, 'moderator')

        # moderators can see counts
        res = app.get(url, auth=user.auth)
        actual = res.json['meta']['reviews_state_counts']
        assert expected == actual

        # exclude private preprints
        preprint_one.node.is_public = False
        preprint_one.node.save()
        expected['pending'] -= 1
        res = app.get(url, auth=user.auth)
        actual = res.json['meta']['reviews_state_counts']
        assert expected == actual

        # exclude deleted preprints
        preprint_two.node.is_deleted = True
        preprint_two.node.save()
        expected['pending'] -= 1
        res = app.get(url, auth=user.auth)
        actual = res.json['meta']['reviews_state_counts']
        assert expected == actual


class TestPreprintProviderPreprintListFilteringByReviewableFields(
        ReviewableFilterMixin):
    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory(reviews_workflow='post-moderation')

    @pytest.fixture()
    def url(self, provider):
        return '/{}preprint_providers/{}/preprints/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def expected_reviewables(self, provider, user):
        preprints = [
            PreprintFactory(
                is_published=False,
                provider=provider,
                project=ProjectFactory(is_public=True)),
            PreprintFactory(
                is_published=False,
                provider=provider,
                project=ProjectFactory(is_public=True)),
            PreprintFactory(
                is_published=False,
                provider=provider,
                project=ProjectFactory(is_public=True)), ]
        preprints[0].run_submit(user)
        preprints[0].run_accept(user, 'comment')
        preprints[1].run_submit(user)
        preprints[2].run_submit(user)
        return preprints

    @pytest.fixture
    def user(self):
        return AuthUserFactory()


class TestPreprintProviderPreprintIsPublishedList(
        PreprintIsPublishedListMixin):

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
    def url(self, provider_one):
        return '/{}preprint_providers/{}/preprints/?version=2.2&'.format(
            API_BASE, provider_one._id)

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

    def test_unpublished_visible_to_admins(
            self, app, user_admin_contrib, preprint_unpublished,
            preprint_published, url):
        res = app.get(url, auth=user_admin_contrib.auth)
        assert len(res.json['data']) == 2
        assert preprint_unpublished._id in [d['id'] for d in res.json['data']]

    def test_unpublished_invisible_to_write_contribs(
            self, app, user_write_contrib, preprint_unpublished,
            preprint_published, url):
        res = app.get(url, auth=user_write_contrib.auth)
        assert len(res.json['data']) == 1
        assert preprint_unpublished._id not in [
            d['id'] for d in res.json['data']]

    def test_filter_published_false_write_contrib(
            self, app, user_write_contrib, url):
        res = app.get(
            '{}filter[is_published]=false'.format(url),
            auth=user_write_contrib.auth)
        assert len(res.json['data']) == 0


class TestPreprintProviderPreprintIsValidList(PreprintIsValidListMixin):

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
    def url(self, provider):
        return '/{}preprint_providers/{}/preprints/?version=2.2&'.format(
            API_BASE, provider._id)
