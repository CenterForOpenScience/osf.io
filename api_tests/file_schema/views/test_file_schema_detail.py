import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    FileSchemaFactory
)

from osf_tests.default_test_schema import DEFAULT_TEST_SCHEMA


@pytest.mark.django_db
class TestFileSchemaDetail:

    @pytest.fixture
    def schema(self):
        return FileSchemaFactory(schema=DEFAULT_TEST_SCHEMA)

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    def test_file_schema_detail_visibility(self, app, user, schema):
        # test_pass_authenticated_user_can_retrieve_schema
        res = app.get(f'/{API_BASE}schemas/files/{schema._id}/', auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']['attributes']
        assert data['name'] == 'FileSchema #0'
        assert data['schema_version'] == 0
        assert res.json['data']['id'] == schema._id

        # test_pass_unauthenticated_user_can_view_schemas
        res = app.get(f'/{API_BASE}schemas/files/{schema._id}/')
        assert res.status_code == 200

        # test_inactive_file_schema_returned
        inactive_schema = FileSchemaFactory(schema=DEFAULT_TEST_SCHEMA, active=False)
        res = app.get(f'/{API_BASE}schemas/files/{inactive_schema._id}/')
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'FileSchema #1'
        assert res.json['data']['attributes']['active'] is False

    def test_file_schema_schema_blocks(self, app, user, schema):
        # test_authenticated_user_can_retrieve_schema_schema_blocks
        res = app.get(f'/{API_BASE}schemas/files/{schema._id}/schema_blocks/', auth=user.auth)
        assert res.status_code == 200

        # test_unauthenticated_user_can_retrieve_schema_schema_blocks
        res = app.get(f'/{API_BASE}schemas/files/{schema._id}/schema_blocks/')
        assert res.status_code == 200

        # test_schema_blocks_detail
        schema_block_id = schema.schema_blocks.first()._id
        res = app.get(f'/{API_BASE}schemas/files/{schema._id}/schema_blocks/', auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == schema_block_id
