import pytest

from api.base.settings.defaults import API_BASE
from api.base.settings import REST_FRAMEWORK
from api.providers.permissions import GroupHelper
from api_tests.providers.preprints.mixins.preprint_provider_mixins import PreprintProviderExistsMixin
from osf_tests.factories import (
    PreprintProviderFactory,
    AuthUserFactory,
)


class TestPreprintProviderExistsForDeprecatedEndpoint(PreprintProviderExistsMixin):
    @pytest.fixture()
    def fake_url(self):
        return '/{}preprint_providers/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider._id)

    @pytest.fixture()
    def provider_url_two(self, preprint_provider_two):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, preprint_provider_two._id)

    @pytest.fixture()
    def provider_preprints_list_url(self, preprint_provider):
        return '/{}preprint_providers/{}/preprints/'.format(API_BASE, preprint_provider._id)

    @pytest.fixture()
    def provider_preprints_list_url_fake(self, fake_url):
        return '{}preprints/'.format(fake_url)

    @pytest.mark.skipif('2.8' not in REST_FRAMEWORK['ALLOWED_VERSIONS'], reason='New API version required to test full deprecation')
    def test_version_deprecation(self, app, provider_url):
        res = app.get('{}?version=2.8'.format(provider_url), expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This route has been deprecated. It was last available in version 2.7'


class TestPreprintProviderExists(PreprintProviderExistsMixin):
    @pytest.fixture()
    def fake_url(self):
        return '/{}providers/preprints/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, preprint_provider):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, preprint_provider._id)

    @pytest.fixture()
    def provider_url_two(self, preprint_provider_two):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, preprint_provider_two._id)

    @pytest.fixture()
    def provider_preprints_list_url(self, preprint_provider):
        return '/{}providers/preprints/{}/submissions/'.format(API_BASE, preprint_provider._id)

    @pytest.fixture()
    def provider_preprints_list_url_fake(self, fake_url):
        return '{}submissions/'.format(fake_url)


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

    @pytest.fixture(params=['/{}preprint_providers/{}/', '/{}providers/preprints/{}/'])
    def url(self, preprint_provider, request):
        url = request.param
        return url.format(
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
