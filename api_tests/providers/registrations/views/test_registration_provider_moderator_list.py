import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationProviderFactory,
)
from api_tests.providers.preprints.views.test_preprint_provider_moderator_list import ProviderModeratorListTestClass


@pytest.mark.django_db
class TestRegistrationProviderModeratorList(ProviderModeratorListTestClass):

    @pytest.fixture()
    def provider(self):
        pp = RegistrationProviderFactory(name='EGAP')
        pp.update_group_permissions()
        return pp

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/moderators/'
