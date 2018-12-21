import pytest

from api.base.settings.defaults import API_BASE

from osf_tests.factories import CollectionProviderFactory
from api_tests.providers.mixins import ProviderLicensesViewTestBaseMixin


class TestCollectionProviderLicenses(ProviderLicensesViewTestBaseMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/collections/{}/licenses/'.format(
            API_BASE, provider._id)
