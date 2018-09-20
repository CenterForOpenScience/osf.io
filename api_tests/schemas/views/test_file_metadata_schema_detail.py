import pytest

from api.base.settings.defaults import API_BASE
from osf.models import FileMetadataSchema
from osf_tests.factories import (
    AuthUserFactory,
)


@pytest.mark.django_db
class TestFileMetadataSchemaDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def schema(self):
        return FileMetadataSchema.objects.filter(name='datacite', active=True).first()

    @pytest.fixture()
    def url(self, schema):
        return '/{}schemas/files/{}/'.format(API_BASE, schema._id)

    def test_schema_detail_crud(self, app, user, schema, url):
        # test_authenticated_user_can_view_schema
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema._id

        # test_cannot_update_schema
        res = app.put_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

        # test_unauthenticated_user_can_view_schema
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema._id

    def test_invalid_schema_not_found(self, app):
        bad_url = '/{}schemas/files/garbage/'.format(API_BASE)
        res = app.get(bad_url, expect_errors=True)
        assert res.status_code == 404
