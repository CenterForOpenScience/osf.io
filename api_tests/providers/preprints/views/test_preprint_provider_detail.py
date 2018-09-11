import pytest

from api.base.settings.defaults import API_BASE
from api.base.settings import REST_FRAMEWORK
from api_tests.providers.mixins import ProviderExistsMixin
from osf_tests.factories import (
    PreprintProviderFactory,
    ProviderAssetFileFactory,
    AuthUserFactory,
)


class TestPreprintProviderExistsForDeprecatedEndpoint(ProviderExistsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return '/{}preprint_providers/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, provider):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def provider_url_two(self, provider_two):
        return '/{}preprint_providers/{}/'.format(
            API_BASE, provider_two._id)

    @pytest.fixture()
    def provider_list_url(self, provider):
        return '/{}preprint_providers/{}/preprints/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return '{}preprints/'.format(fake_url)

    @pytest.mark.skipif('2.8' not in REST_FRAMEWORK['ALLOWED_VERSIONS'], reason='New API version required to test full deprecation')
    def test_version_deprecation(self, app, provider_url):
        res = app.get('{}?version=2.8'.format(provider_url), expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'This route has been deprecated. It was last available in version 2.7'


class TestPreprintProviderExists(ProviderExistsMixin):
    provider_class = PreprintProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return '/{}providers/preprints/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, provider):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def provider_url_two(self, provider_two):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, provider_two._id)

    @pytest.fixture()
    def provider_list_url(self, provider):
        return '/{}providers/preprints/{}/preprints/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return '{}preprints/'.format(fake_url)


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
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def admin(self, provider):
        user = AuthUserFactory()
        user.groups.add(provider.get_group('admin'))
        return user

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        user.groups.add(provider.get_group('moderator'))
        return user

    @pytest.fixture(params=['/{}preprint_providers/{}/', '/{}providers/preprints/{}/'])
    def url(self, provider, request):
        url = request.param
        return url.format(
            API_BASE, provider._id)

    def test_update_reviews_settings(
            self, app, provider, url, admin, moderator):
        payload = self.settings_payload(
            provider.id,
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
            provider.id,
            reviews_workflow='pre-moderation',
            reviews_comments_private=False,
        )
        res = app.patch_json_api(
            url, partial_payload,
            auth=admin.auth, expect_errors=True)
        assert res.status_code == 400

        partial_payload = self.settings_payload(
            provider.id,
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
        provider.refresh_from_db()
        assert provider.reviews_workflow == 'pre-moderation'
        assert not provider.reviews_comments_private
        assert not provider.reviews_comments_anonymous

        # ...but only once
        res = app.patch_json_api(
            url, payload, auth=admin.auth,
            expect_errors=True)
        assert res.status_code == 409

        another_payload = self.settings_payload(
            provider.id,
            reviews_workflow='post-moderation',
            reviews_comments_private=True,
            reviews_comments_anonymous=True
        )
        res = app.patch_json_api(
            url, another_payload,
            auth=admin.auth, expect_errors=True)
        assert res.status_code == 409

        provider.refresh_from_db()
        assert provider.reviews_workflow == 'pre-moderation'
        assert not provider.reviews_comments_private
        assert not provider.reviews_comments_anonymous


@pytest.mark.django_db
class TestPreprintProviderAssets:
    @pytest.fixture()
    def provider_one(self):
        return PreprintProviderFactory(name='Hanarxiv')

    @pytest.fixture()
    def provider_two(self):
        return PreprintProviderFactory(name='Leileirxiv')

    @pytest.fixture()
    def provider_asset_one(self, provider_one):
        return ProviderAssetFileFactory(providers=[provider_one])

    @pytest.fixture()
    def provider_asset_two(self, provider_two):
        return ProviderAssetFileFactory(providers=[provider_two])

    @pytest.fixture()
    def provider_one_url(self, provider_one):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, provider_one._id)

    @pytest.fixture()
    def provider_two_url(self, provider_two):
        return '/{}providers/preprints/{}/'.format(
            API_BASE, provider_two._id)

    def test_asset_attribute_correct(self, app, provider_one, provider_two, provider_asset_one, provider_asset_two,
                                     provider_one_url, provider_two_url):
        res = app.get(provider_one_url)
        assert res.json['data']['attributes']['assets'][provider_asset_one.name] == provider_asset_one.file.url

        res = app.get(provider_two_url)
        assert res.json['data']['attributes']['assets'][provider_asset_two.name] == provider_asset_two.file.url
