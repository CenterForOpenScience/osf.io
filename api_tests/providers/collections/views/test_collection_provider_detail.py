import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderExistsMixin
from osf_tests.factories import (
    CollectionProviderFactory,
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
