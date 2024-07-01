import pytest

from api.base.settings.defaults import API_BASE
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,

)
from osf import features
from django.contrib.auth.models import Group
from waffle.models import Flag

@pytest.mark.django_db
class TestSchemaList:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def factory_request(self, rf, url, user):
        request = rf.get(url)
        request.user = user
        return request

    @pytest.fixture
    def url(self):
        return f'/{API_BASE}schemas/registrations/?version=2.11'

    @pytest.fixture
    def egap_admin(self):
        user = AuthUserFactory()
        user.save()
        flag = Flag.objects.create(name=features.EGAP_ADMINS)
        group = Group.objects.create(name=features.EGAP_ADMINS)  # Just using the same name for convenience
        flag.groups.add(group)
        group.user_set.add(user)
        group.save()
        flag.save()
        return user

    def test_schemas_list_crud(self, app, url, user, egap_admin, factory_request):
        # test_pass_authenticated_user_can_view_schemas
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['meta']['total'] == RegistrationSchema.objects.get_latest_versions(factory_request).count()

        # test_cannot_update_metaschemas
        res = app.put_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_cannot_post_metaschemas
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_pass_unauthenticated_user_can_view_schemas
        res = app.get(url)
        assert res.status_code == 200

        # test_filter_on_active
        url = f'/{API_BASE}schemas/registrations/?version=2.11&filter[active]=True'
        res = app.get(url)

        assert res.status_code == 200
        active_schemas = RegistrationSchema.objects.get_latest_versions(factory_request).filter(active=True)
        assert res.json['meta']['total'] == active_schemas.count()

        url = f'/{API_BASE}schemas/registrations/'
        # test_make_sure_egap_admins_can_view_registrations

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert not [data for data in res.json['data'] if data['attributes']['name'] == 'EGAP Registration']
