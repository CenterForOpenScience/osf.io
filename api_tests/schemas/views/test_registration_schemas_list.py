import pytest

from waffle.testutils import override_switch

from api.base.settings.defaults import API_BASE
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,
)
from osf.features import ENABLE_INACTIVE_SCHEMAS
from osf.management.commands.add_egap_admin import create_egap_admins_group

@pytest.mark.django_db
class TestSchemaList:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def egap_admin(self):
        user = AuthUserFactory(username='greg@egap.com')
        user.save()
        create_egap_admins_group(user.username)
        return user

    def test_schemas_list_crud(self, app):

        user = AuthUserFactory()
        url = '/{}schemas/registrations/?version=2.11'.format(API_BASE)
        # test_pass_authenticated_user_can_view_schemas

        with override_switch(ENABLE_INACTIVE_SCHEMAS, active=False):
            res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['meta']['total'] == RegistrationSchema.objects.get_latest_versions().count()

        with override_switch(ENABLE_INACTIVE_SCHEMAS, active=True):
            res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['meta']['total'] == RegistrationSchema.objects.get_latest_versions(only_active=False).count()

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
        url = '/{}schemas/registrations/?version=2.11&filter[active]=True'.format(API_BASE)
        with override_switch(ENABLE_INACTIVE_SCHEMAS, active=True):
            res = app.get(url)

        assert res.status_code == 200
        assert res.json['meta']['total'] == RegistrationSchema.objects.get_latest_versions().count()

    def test_egap_schema_visible_to_admins(self, app, user, egap_admin):
        url = '/{}schemas/registrations/'.format(API_BASE)
        # test_pass_authenticated_user_can_view_schemas

        with override_switch(ENABLE_INACTIVE_SCHEMAS, active=True):
            res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert not [data for data in res.json['data'] if data['attributes']['name'] == 'EGAP Registration']

        with override_switch(ENABLE_INACTIVE_SCHEMAS, active=True):
            res = app.get(url, auth=egap_admin.auth)
        assert res.status_code == 200
        assert [data for data in res.json['data'] if data['attributes']['name'] == 'EGAP Registration']
