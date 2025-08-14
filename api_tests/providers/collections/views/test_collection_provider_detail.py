import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderExistsMixin
from osf_tests.factories import (
    CollectionProviderFactory,
    BrandFactory,
)


class TestCollectionProviderExists(ProviderExistsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return f'/{API_BASE}providers/collections/fake/'

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
        return f'/{API_BASE}providers/collections/{provider._id}/submissions/'

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return f'{fake_url}submissions/'

    @pytest.fixture()
    def brand(self):
        return BrandFactory()

    @pytest.fixture()
    def provider_with_brand(self, brand):
        registration_provider = CollectionProviderFactory()
        registration_provider.brand = brand
        registration_provider.save()
        return registration_provider

    @pytest.fixture()
    def provider_url_w_brand(self, provider_with_brand):
        return f'/{API_BASE}providers/collections/{provider_with_brand._id}/'

    def test_registration_provider_with_special_fields(self, app, provider_with_brand, brand, provider_url_w_brand):
        res = app.get(provider_url_w_brand)

        assert res.status_code == 200
        data = res.json['data']

        assert data['relationships']['brand']['data']['id'] == str(brand.id)
