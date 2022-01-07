import pytest

from api.base.settings.defaults import API_BASE
from osf.models.schema import FileSchema
from osf_tests.factories import (
    AuthUserFactory,

)


@pytest.mark.django_db
class TestFileSchemaList:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def url(self):
        return f'/{API_BASE}schemas/files/'

    def test_schemas_list_crud(self, app, url, user):
        # test_pass_authenticated_user_can_view_schemas
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['links']['meta']['total'] == FileSchema.objects.count()

        # test_cannot_update_file_schema
        res = app.put_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_cannot_post_file_schema
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_pass_unauthenticated_user_can_view_file_schema
        res = app.get(url)
        assert res.status_code == 200

        # test_filter_on_active
        res = app.get(f'{url}?filter[active]=True')
        assert res.status_code == 200
        active_schemas = FileSchema.objects.filter(active=True)
        assert res.json['links']['meta']['total'] == active_schemas.count()

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert not [data for data in res.json['data'] if data['attributes']['name'] == 'FileSchema #0']
