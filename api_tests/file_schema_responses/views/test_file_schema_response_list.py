import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
)


@pytest.mark.django_db
class TestFileSchemaResponseList:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def file(self, user):
        public_node = ProjectFactory(creator=user, is_public=True)
        return utils.create_test_file(public_node, user, filename='public_file')

    @pytest.fixture
    def url(self, file):
        return f'/{API_BASE}files/{file._id}/schema_responses/'

    def test_file_schema_response_list(self, app, url, user, file):

        # test_unauthenticated_can_view_public_file_metadata_records
        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == file.schema_responses.count()

        # test_authenticated_can_view_public_file_metadata_records
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == file.schema_responses.count()

        # test_unauthenticated_cannot_view_private_file_metadata_records
        res = app.get(url, expect_errors=True)
        assert res.status_code == 200

        # test_authenticated_can_view_private_file_metadata_records
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == file.schema_responses.count()

        # test_unauthorized_cannot_view_private_file_metadata_records
        unauth = AuthUserFactory()
        res = app.get(url, auth=unauth.auth, expect_errors=True)
        assert res.status_code == 200

        # test_cannot_create_metadata_records
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405
