import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import (
    ProviderSpecificSubjectsMixin,
    ProviderHighlightedSubjectsMixin,
    ProviderCustomTaxonomyMixin,
    ProviderCustomSubjectMixin,
)

from osf_tests.factories import CollectionProviderFactory


class TestProviderSpecificTaxonomies(ProviderSpecificSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/collections/{provider_1._id}/taxonomies/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/collections/{provider_2._id}/taxonomies/?page[size]=15&'


class TestProviderHighlightedTaxonomies(ProviderHighlightedSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/collections/{provider._id}/taxonomies/highlighted/'


class TestCustomTaxonomy(ProviderCustomTaxonomyMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/collections/{}/taxonomies/'


class TestProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/collections/{provider_1._id}/subjects/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/collections/{provider_2._id}/subjects/?page[size]=15&'


class TestProviderHighlightedSubjects(ProviderHighlightedSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/collections/{provider._id}/subjects/highlighted/'


class TestCustomSubjects(ProviderCustomSubjectMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/collections/{}/subjects/'
