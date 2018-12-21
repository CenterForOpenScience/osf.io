import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderListViewTestBaseMixin

from osf_tests.factories import (
    CollectionProviderFactory,
)


class TestCollectionProviderList(ProviderListViewTestBaseMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, request):
        return '/{}providers/collections/'.format(API_BASE)
