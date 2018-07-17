import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderDetailViewTestBaseMixin
from osf_tests.factories import (
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
