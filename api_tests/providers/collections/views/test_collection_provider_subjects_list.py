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
        return '/{}providers/collections/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}providers/collections/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)


class TestProviderHighlightedTaxonomies(ProviderHighlightedSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/collections/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)


class TestCustomTaxonomy(ProviderCustomTaxonomyMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/collections/{}/taxonomies/'


class TestProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}providers/collections/{}/subjects/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}providers/collections/{}/subjects/?page[size]=15&'.format(API_BASE, provider_2._id)


class TestProviderHighlightedSubjects(ProviderHighlightedSubjectsMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/collections/{}/subjects/highlighted/'.format(API_BASE, provider._id)


class TestCustomSubjects(ProviderCustomSubjectMixin):
    provider_class = CollectionProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/collections/{}/subjects/'
