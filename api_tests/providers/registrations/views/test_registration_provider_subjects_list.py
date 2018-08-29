import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderSpecificSubjectsMixin, ProviderHighlightedSubjectsMixin, ProviderCustomTaxonomyMixin

from osf_tests.factories import RegistrationProviderFactory


class TestRegistrationProviderSpecificSubjects(ProviderSpecificSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url_1(self, provider_1):
        return '/{}providers/registrations/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_1._id)

    @pytest.fixture()
    def url_2(self, provider_2):
        return '/{}providers/registrations/{}/taxonomies/?page[size]=15&'.format(API_BASE, provider_2._id)


class TestRegistrationProviderHighlightedSubjects(ProviderHighlightedSubjectsMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self, provider):
        return '/{}providers/registrations/{}/taxonomies/highlighted/'.format(API_BASE, provider._id)


class TestRegistrationProviderCustomTaxonomy(ProviderCustomTaxonomyMixin):
    provider_class = RegistrationProviderFactory

    @pytest.fixture()
    def url(self):
        return '/{}providers/registrations/{}/taxonomies/'
