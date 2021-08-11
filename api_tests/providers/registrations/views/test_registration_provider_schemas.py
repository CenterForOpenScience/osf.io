import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationProviderFactory,
    AuthUserFactory
)
from django.contrib.auth.models import Group


from osf.models import RegistrationSchema
from waffle.models import Flag

from osf.migrations import update_provider_auth_groups
from osf.features import EGAP_ADMINS


@pytest.mark.django_db
class TestRegistrationProviderSchemas:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def egap_flag(self):
        flag = Flag.objects.get(name='egap_admins')
        flag.everyone = True
        flag.save()
        return flag

    @pytest.fixture()
    def schema(self):
        reg_schema = RegistrationSchema.objects.get(name='OSF Preregistration', schema_version=2)
        reg_schema.active = True
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def egap_schema(self):
        schema = RegistrationSchema.objects.get(name='EGAP Registration', schema_version=3)
        schema.visible = True
        schema.active = True
        schema.save()
        return schema

    @pytest.fixture()
    def out_dated_schema(self):
        reg_schema = RegistrationSchema(name='Old Schema', schema_version=1)
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def osf_reg_schema(self):
        osf_reg = RegistrationSchema.objects.get(name='OSF Preregistration', schema_version=3)
        osf_reg.visible = True
        osf_reg.active = True
        osf_reg.save()
        return osf_reg

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
    def provider_with_v2_reg_only(self, schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(schema)
        provider.save()
        return provider

    @pytest.fixture()
    def provider_with_egap_only(self, egap_schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(egap_schema)
        provider.save()
        return provider

    @pytest.fixture()
    def provider_with_reg(self, osf_reg_schema, egap_schema, schema, out_dated_schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(*[osf_reg_schema, schema, out_dated_schema, egap_schema])
        provider.save()
        return provider

    @pytest.fixture
    def egap_admin(self):
        user = AuthUserFactory()
        user.save()
        flag = Flag.objects.get(name=EGAP_ADMINS)
        group = Group.objects.create(name=EGAP_ADMINS)  # Just using the same name for convenience
        flag.groups.add(group)
        group.user_set.add(user)
        group.save()
        flag.save()
        return user

    @pytest.fixture()
    def url(self, provider):
        return f'/{API_BASE}providers/registrations/{provider._id}/schemas/'

    @pytest.fixture()
    def url_with_v2_reg_only(self, provider_with_v2_reg_only):
        return f'/{API_BASE}providers/registrations/{provider_with_v2_reg_only._id}/schemas/'

    @pytest.fixture()
    def url_with_egap_only(self, provider_with_egap_only):
        return f'/{API_BASE}providers/registrations/{provider_with_egap_only._id}/schemas/'

    @pytest.fixture()
    def url_with_reg(self, provider_with_reg):
        return f'/{API_BASE}providers/registrations/{provider_with_reg._id}/schemas/'

    def test_registration_provider_with_schema(
            self,
            app,
            url,
            schema,
            egap_schema,
            egap_admin,
            invisible_schema,
            user,
            url_with_v2_reg_only,
            url_with_egap_only
    ):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 3
        assert schema._id in [item['id'] for item in data]
        assert invisible_schema._id in [item['id'] for item in data]
        assert schema.name in [item['attributes']['name'] for item in data]

        res = app.get(url_with_v2_reg_only, auth=egap_admin.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 1
        assert data[0]['id'] == schema._id
        assert data[0]['attributes']['name'] == schema.name

        res = app.get(url_with_egap_only, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 0

    def test_egap_registration_schema(
            self,
            app,
            user,
            egap_admin,
            egap_schema,
            url_with_egap_only
    ):
        res = app.get(url_with_egap_only, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 0

        res = app.get(url_with_egap_only, auth=egap_admin.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 1
        assert data[0]['id'] == egap_schema._id
        assert data[0]['attributes']['name'] == egap_schema.name

    def test_registration_provider_with_default_schema(
            self,
            app,
            provider_with_reg,
            out_dated_schema,
            user,
            egap_schema,
            schema,
            url_with_reg,
            osf_reg_schema
    ):
        provider_with_reg.default_schema = osf_reg_schema
        provider_with_reg.save()
        res = app.get(url_with_reg, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert provider_with_reg.schemas.all().count() == 4
        assert len(data) == 2
        assert osf_reg_schema._id == data[0]['id']
        assert schema.name in [item['attributes']['name'] for item in data]
