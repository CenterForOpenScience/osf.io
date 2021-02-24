import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationProviderFactory,
)
from api_tests.providers.preprints.views.test_preprint_provider_moderator_detail import ProviderModeratorDetailTestClass


@pytest.mark.django_db
class TestRegistrationProviderModeratorDetail(ProviderModeratorDetailTestClass):

    @pytest.fixture()
    def provider(self):
        pp = RegistrationProviderFactory(name='EGAP')
        pp.update_group_permissions()
        return pp

    @pytest.fixture()
    def url(self, provider, request):
        return f'/{API_BASE}providers/registrations/{provider._id}/moderators/{{}}/'
