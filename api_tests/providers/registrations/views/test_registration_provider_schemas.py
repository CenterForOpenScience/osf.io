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
        return RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)

    @pytest.fixture()
    def egap_schema(self):
        return RegistrationSchema.objects.get(name='EGAP Registration', schema_version=3)

    @pytest.fixture()
    def out_dated_schema(self):
        reg_schema = RegistrationSchema(name='Prereg Challenge', schema_version=1)
        reg_schema.save()
        return reg_schema

    @pytest.fixture()
    def osf_prereg_schema(self):
        osf_prereg = RegistrationSchema.objects.get(name='OSF Preregistration', schema_version=3)
        osf_prereg.visible = True
        osf_prereg.save()
        return osf_prereg

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
    def provider_with_v2_prereg_only(self, schema):
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
    def provider_with_prereg(self, osf_prereg_schema, egap_schema, schema, out_dated_schema):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.schemas.add(*[osf_prereg_schema, schema, out_dated_schema, egap_schema])
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
    def url_with_v2_prereg_only(self, provider_with_v2_prereg_only):
        return f'/{API_BASE}providers/registrations/{provider_with_v2_prereg_only._id}/schemas/'

    @pytest.fixture()
    def url_with_egap_only(self, provider_with_egap_only):
        return f'/{API_BASE}providers/registrations/{provider_with_egap_only._id}/schemas/'

    @pytest.fixture()
    def url_with_prereg(self, provider_with_prereg):
        return f'/{API_BASE}providers/registrations/{provider_with_prereg._id}/schemas/'

    def test_registration_provider_with_schema(
            self,
            app,
            url,
            schema,
            egap_schema,
            egap_admin,
            invisible_schema,
            user,
            url_with_v2_prereg_only,
            url_with_egap_only
    ):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 2
        assert schema._id in [item['id'] for item in data]
        assert invisible_schema._id in [item['id'] for item in data]
        assert schema.name in [item['attributes']['name'] for item in data]

        res = app.get(url_with_v2_prereg_only, auth=egap_admin.auth)
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
            provider_with_prereg,
            out_dated_schema,
            user,
            egap_schema,
            schema,
            url_with_prereg,
            osf_prereg_schema
    ):
        provider_with_prereg.default_schema = osf_prereg_schema
        provider_with_prereg.save()
        res = app.get(url_with_prereg, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert len(data) == 3
        assert osf_prereg_schema._id == data[0]['id']
        assert schema.name in [item['attributes']['name'] for item in data]
