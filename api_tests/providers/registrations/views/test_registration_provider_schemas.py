import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationProviderFactory,
    AuthUserFactory
)

from osf.models import RegistrationSchema

from osf.migrations import update_provider_auth_groups

@pytest.mark.django_db
class TestRegistrationProviderSchemas:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        provider.get_group('moderator').user_set.add(user)
        return user

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)

    @pytest.fixture()
    def provider(self, schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(schema)
        provider.save()
        return provider

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/schemas/'

    def test_registration_provider_with_schema(self, app, url, provider, schema, user, moderator):
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.get(url, auth=moderator.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 1
        assert data[0]['id'] == schema._id
        assert data[0]['attributes']['name'] == 'Prereg Challenge'
