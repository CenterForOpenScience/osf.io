import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderListViewTestBaseMixin

from osf_tests.factories import (
    RegistrationProviderFactory,
)


class TestRegistrationProviderList(ProviderListViewTestBaseMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, request):
        return '/{}providers/registrations/'.format(API_BASE)
