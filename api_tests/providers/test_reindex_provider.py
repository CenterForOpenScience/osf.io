import pytest
import json

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

    def test_reindex_provider_preprint(self, mock_share, preprint_provider, preprint):
        call_command('reindex_provider', f'--providers={preprint_provider._id}')
        data = json.loads(mock_share.calls[-1].request.body)

        assert any(graph for graph in data['data']['attributes']['data']['@graph']
                   if graph['@type'] == preprint_provider.share_publish_type.lower())

    def test_reindex_provider_registration(self, mock_share, registration_provider, registration):
        call_command('reindex_provider', f'--providers={registration_provider._id}')
        data = json.loads(mock_share.calls[-1].request.body)

        assert any(graph for graph in data['data']['attributes']['data']['@graph']
                   if graph['@type'] == registration_provider.share_publish_type.lower())
