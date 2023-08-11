from unittest import mock

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

    @pytest.fixture()
    def mock_update_share(self):
        with mock.patch('osf.management.commands.reindex_provider.update_share') as _mock_update_share:
            yield _mock_update_share

    def test_reindex_provider_preprint(self, mock_update_share, preprint_provider, preprint):
        call_command('reindex_provider', f'--providers={preprint_provider._id}')
        assert mock_update_share.called_once_with(preprint)

    def test_reindex_provider_registration(self, mock_update_share, registration_provider, registration):
        call_command('reindex_provider', f'--providers={registration_provider._id}')
        assert mock_update_share.called_once_with(registration)
