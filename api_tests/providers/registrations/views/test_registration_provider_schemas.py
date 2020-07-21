import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationProviderFactory,
)

from osf.models import RegistrationSchema

from osf.migrations import update_provider_auth_groups


@pytest.mark.django_db
class TestRegistrationProviderSchemas:

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)

    @pytest.fixture()
    def out_dated_schema(self):
        reg_schema = RegistrationSchema(name='Prereg Challenge', schema_version=1)
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def invisible_schema(self):
        reg_schema = RegistrationSchema(name='Test Schema (Invisible)', schema_version=1, visible=False)
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def inactive_schema(self):
        reg_schema = RegistrationSchema(name='Test Schema (Inactive)', schema_version=1, active=False)
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def provider(self, schema, out_dated_schema, invisible_schema, inactive_schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(*[schema, out_dated_schema, invisible_schema, inactive_schema])
        provider.save()
        return provider

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/schemas/'

    def test_registration_provider_with_schema(self, app, url, provider, schema):
        res = app.get(url)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 1
        assert data[0]['id'] == schema._id
        assert data[0]['attributes']['name'] == schema.name
