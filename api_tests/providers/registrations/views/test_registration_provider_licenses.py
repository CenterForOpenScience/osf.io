import pytest

from api.base.settings.defaults import API_BASE

from osf_tests.factories import RegistrationProviderFactory
from api_tests.providers.mixins import ProviderLicensesViewTestBaseMixin


class TestRegistrationProviderLicenses(ProviderLicensesViewTestBaseMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/registrations/{}/licenses/'.format(
            API_BASE, provider._id)
