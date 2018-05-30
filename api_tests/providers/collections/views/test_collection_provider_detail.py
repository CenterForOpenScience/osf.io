import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderExistsMixin
from osf_tests.factories import (
    CollectionProviderFactory,
)


class TestPreprintProviderExists(ProviderExistsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return '/{}providers/collections/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, provider):
        return '/{}providers/collections/{}/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def provider_url_two(self, provider_two):
        return '/{}providers/collections/{}/'.format(
            API_BASE, provider_two._id)

    @pytest.fixture()
    def provider_list_url(self, provider):
        return '/{}providers/collections/{}/submissions/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return '{}submissions/'.format(fake_url)

    # This overrides the mixin to prevent not-yet-implemented behavior
    # TODO [IN-153]: use mixin implmentation
    def test_provider_exists(self, app, provider_url, fake_url, provider_list_url, provider_list_url_fake):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        #res = app.get(provider_list_url)
        #assert res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

        #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get(
            '{}licenses/'.format(fake_url),
            expect_errors=True)
        assert licenses_res.status_code == 404

        res = app.get(
            provider_list_url_fake,
            expect_errors=True)
        assert res.status_code == 404

        taxonomies_res = app.get(
            '{}taxonomies/'.format(fake_url),
            expect_errors=True)
        assert taxonomies_res.status_code == 404
