import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import (
    ProviderSpecificSubjectsMixin,
    ProviderHighlightedSubjectsMixin,
    ProviderCustomTaxonomyMixin,
    ProviderCustomSubjectMixin,
)

from osf_tests.factories import RegistrationProviderFactory


class TestRegistrationProviderSpecificTaxonomies(ProviderSpecificSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/registrations/{provider_1._id}/taxonomies/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/registrations/{provider_2._id}/taxonomies/?page[size]=15&'


class TestRegistrationProviderHighlightedTaxonomies(ProviderHighlightedSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/taxonomies/highlighted/'


class TestRegistrationProviderCustomTaxonomy(ProviderCustomTaxonomyMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/registrations/{}/taxonomies/'


class TestRegistrationProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return f'/{API_BASE}providers/registrations/{provider_1._id}/subjects/?page[size]=15&'

    @pytest.fixture()
    def url_2(self, provider_2):
        return f'/{API_BASE}providers/registrations/{provider_2._id}/subjects/?page[size]=15&'


class TestRegistrationProviderHighlightedSubjects(ProviderHighlightedSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/subjects/highlighted/'


class TestRegistrationProviderCustomSubjects(ProviderCustomSubjectMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/registrations/{}/subjects/'
