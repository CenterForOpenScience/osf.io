import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import OnlyModeratorOrAdminPermissionsMixin

from osf_tests.factories import PreprintProviderFactory


@pytest.mark.django_db
class TestOnlyModeratorOrAdmin(OnlyModeratorOrAdminPermissionsMixin):

    @pytest.fixture()
    def urls(self, provider, moderator, admin):
        return [
            f'/{API_BASE}providers/preprints/{provider._id}/withdraw_requests/',
            f'/{API_BASE}providers/preprints/{provider._id}/moderators/',
            f'/{API_BASE}providers/preprints/{provider._id}/moderators/{moderator._id}/',
            f'/{API_BASE}providers/preprints/{provider._id}/moderators/{admin._id}/',
        ]

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()
