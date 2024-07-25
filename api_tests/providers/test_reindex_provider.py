import pytest

from django.core.management import call_command

from osf_tests.factories import (
    PreprintFactory,
    PreprintProviderFactory,
    RegistrationProviderFactory,
    RegistrationFactory,
    AuthUserFactory
)


@pytest.mark.django_db
class TestReindexProvider:

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def preprint(self, preprint_provider):
        return PreprintFactory(provider=preprint_provider)

    @pytest.fixture()
    def registration_provider(self):
        return RegistrationProviderFactory()

    @pytest.fixture()
    def registration(self, registration_provider):
        return RegistrationFactory(provider=registration_provider)

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    def test_reindex_provider_preprint(self, mock_update_share, preprint_provider, preprint):
        mock_update_share.reset_mock()
        call_command('reindex_provider', f'--providers={preprint_provider._id}')
        mock_update_share.assert_called_once_with(preprint)

    def test_reindex_provider_registration(self, mock_update_share, registration_provider, registration):
        mock_update_share.reset_mock()
        call_command('reindex_provider', f'--providers={registration_provider._id}')
        mock_update_share.assert_called_once_with(registration)
