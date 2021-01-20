import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderDetailViewTestBaseMixin
from osf_tests.factories import (
    BrandFactory,
    RegistrationProviderFactory,
)


class TestRegistrationProviderExists(ProviderDetailViewTestBaseMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def fake_url(self):
        return '/{}providers/registrations/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, provider):
        return '/{}providers/registrations/{}/'.format(
            API_BASE, provider._id)

    @pytest.fixture()
    def provider_url_two(self, provider_two):
        return '/{}providers/registrations/{}/'.format(
            API_BASE, provider_two._id)

    @pytest.fixture()
    def provider_list_url(self, provider):
        return '/{}providers/registrations/{}/submissions/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def provider_list_url_fake(self, fake_url):
        return '{}submissions/'.format(fake_url)

    @pytest.fixture()
    def brand(self):
        return BrandFactory()

    @pytest.fixture()
    def provider_with_brand(self, brand):
        registration_provider = RegistrationProviderFactory()
        registration_provider.brand = brand
        registration_provider.save()
        return registration_provider

    @pytest.fixture()
    def provider_url_w_brand(self, provider_with_brand):
        return '/{}providers/registrations/{}/'.format(
            API_BASE, provider_with_brand._id)

    def test_registration_provider_with_special_fields(self, app, provider_with_brand, brand, provider_url_w_brand):
        # Ensures brand data is included for registration providers
        res = app.get(provider_url_w_brand)

        assert res.status_code == 200
        data = res.json['data']

        assert data['relationships']['brand']['data']['id'] == str(brand.id)
        assert data['attributes']['branded_discovery_page'] == provider_with_brand.branded_discovery_page
