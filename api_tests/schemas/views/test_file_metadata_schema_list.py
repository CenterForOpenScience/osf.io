import pytest

from api.base.settings.defaults import API_BASE
from osf.models.metaschema import FileMetadataSchema
from osf_tests.factories import (
    AuthUserFactory,
)


@pytest.mark.django_db
class TestFileMetadataSchemaList:

    def test_schema_list_crud(self, app):

        user = AuthUserFactory()
        url = '/{}schemas/files/'.format(API_BASE)

        # test_authenticated_user_can_view_schemas
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert (len(res.json['data']) == FileMetadataSchema.objects.filter(active=True).count())

        # test_cannot_create_schemas
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_unauthenticated_user_can_view_schemas
        res = app.get(url)
        assert res.status_code == 200
