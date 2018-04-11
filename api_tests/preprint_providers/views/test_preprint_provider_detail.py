import pytest

from api.base.settings.defaults import API_BASE
from api.preprint_providers.permissions import GroupHelper
from osf_tests.factories import (
    PreprintProviderFactory,
    AuthUserFactory,
    SubjectFactory,
)


@pytest.mark.django_db
class TestPreprintProviderExists:

    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def preprint_provider_two(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def fake_url(self):
        return '/{}preprint_providers/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider._id)

    def test_preprint_provider_exists(self, app, provider_url, fake_url):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        preprints_res = app.get('{}preprints/'.format(provider_url))
        assert preprints_res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

    #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get(
            '{}licenses/'.format(fake_url),
            expect_errors=True)
        assert licenses_res.status_code == 404

        preprints_res = app.get(
            '{}preprints/'.format(fake_url),
            expect_errors=True)
        assert preprints_res.status_code == 404

        taxonomies_res = app.get(
            '{}taxonomies/'.format(fake_url),
            expect_errors=True)
        assert taxonomies_res.status_code == 404

    def test_has_highlighted_subjects_flag(
            self, app, preprint_provider,
            preprint_provider_two, provider_url):
        SubjectFactory(
            provider=preprint_provider,
            text='A', highlighted=True)
        SubjectFactory(provider=preprint_provider_two, text='B')

        res = app.get(provider_url)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is True

        url_provider_two = '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider_two._id)
        res = app.get(url_provider_two)
        assert res.status_code == 200
        res_subjects = res.json['data']['relationships']['highlighted_taxonomies']
        assert res_subjects['links']['related']['meta']['has_highlighted_subjects'] is False


@pytest.mark.django_db
class TestPreprintProviderUpdate:

    def settings_payload(self, provider_id, jsonapi_type='preprintproviders', **kwargs):
        payload = {
            'data': {
                'id': provider_id,
                'type': jsonapi_type,
                'attributes': kwargs
            }
        }
        return payload

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def admin(self, preprint_provider):
        user = AuthUserFactory()
        user.groups.add(GroupHelper(preprint_provider).get_group('admin'))
        return user

    @pytest.fixture()
    def moderator(self, preprint_provider):
        user = AuthUserFactory()
        user.groups.add(GroupHelper(preprint_provider).get_group('moderator'))
        return user

    @pytest.fixture()
    def url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider._id)

    def test_update_reviews_settings(
            self, app, preprint_provider, url, admin, moderator):
        payload = self.settings_payload(
            preprint_provider.id,
            reviews_workflow='pre-moderation',
            reviews_comments_private=False,
            reviews_comments_anonymous=False
        )

        # Unauthorized user can't set up moderation
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        # Random user can't set up moderation
        some_rando = AuthUserFactory()
        res = app.patch_json_api(
            url, payload, auth=some_rando.auth,
            expect_errors=True)
        assert res.status_code == 403

        # Moderator can't set up moderation
        res = app.patch_json_api(
            url, payload, auth=moderator.auth,
            expect_errors=True)
        assert res.status_code == 403

        # Admin must include all settings
        partial_payload = self.settings_payload(
            preprint_provider.id,
            reviews_workflow='pre-moderation',
            reviews_comments_private=False,
        )
        res = app.patch_json_api(
            url, partial_payload,
            auth=admin.auth, expect_errors=True)
        assert res.status_code == 400

        partial_payload = self.settings_payload(
            preprint_provider.id,
            reviews_comments_private=False,
            reviews_comments_anonymous=False,
        )
        res = app.patch_json_api(
            url, partial_payload,
            auth=admin.auth, expect_errors=True)
        assert res.status_code == 400

        # Admin can set up moderation
        res = app.patch_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 200
        preprint_provider.refresh_from_db()
        assert preprint_provider.reviews_workflow == 'pre-moderation'
        assert not preprint_provider.reviews_comments_private
        assert not preprint_provider.reviews_comments_anonymous

        # ...but only once
        res = app.patch_json_api(
            url, payload, auth=admin.auth,
            expect_errors=True)
        assert res.status_code == 409

        another_payload = self.settings_payload(
            preprint_provider.id,
            reviews_workflow='post-moderation',
            reviews_comments_private=True,
            reviews_comments_anonymous=True
        )
        res = app.patch_json_api(
            url, another_payload,
            auth=admin.auth, expect_errors=True)
        assert res.status_code == 409

        preprint_provider.refresh_from_db()
        assert preprint_provider.reviews_workflow == 'pre-moderation'
        assert not preprint_provider.reviews_comments_private
        assert not preprint_provider.reviews_comments_anonymous
