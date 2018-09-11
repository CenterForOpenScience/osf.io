import pytest

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
        url = '/{}schemas/registrations/'.format(API_BASE)

        # test_pass_authenticated_user_can_view_schemas
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == RegistrationSchema.objects.filter(
            active=True, schema_version=LATEST_SCHEMA_VERSION).count())

        # test_cannot_update_metaschemas
        res = app.put_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_cannot_post_metaschemas
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_pass_unauthenticated_user_can_view_schemas
        res = app.get(url)
        assert res.status_code == 200
