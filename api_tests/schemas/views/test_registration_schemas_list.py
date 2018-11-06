import pytest
import waffle

from api.base.settings.defaults import API_BASE
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import (
    AuthUserFactory,
)
from website.project.metadata.schemas import LATEST_SCHEMA_VERSION


@pytest.mark.django_db
class TestSchemaList:

    def test_schemas_list_crud(self, app):

        user = AuthUserFactory()
        url = '/{}schemas/registrations/?version=2.11'.format(API_BASE)
        schemas = RegistrationSchema.objects.filter(schema_version=LATEST_SCHEMA_VERSION)
        # test_pass_authenticated_user_can_view_schemas
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        if waffle.switch_is_active('filter_schemas_registration_on_active'):
            assert res.json['meta']['total'] == schemas.count()
        else:
            assert res.json['meta']['total'] == schemas.filter(active=True).count()

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
        if waffle.switch_is_active('filter_schemas_registration_on_active'):
            # test_filter_on_active
            url = '/{}schemas/registrations/?version=2.11&filter[active]=True'.format(API_BASE)
            res = app.get(url)
            assert res.status_code == 200
            assert res.json['meta']['total'] == schemas.filter(active=True).count()
