import pytest

from api.base.settings.defaults import API_BASE
from osf.models import (
    NodeLog,
)
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    FileSchemaResponseFactory,
    FileSchemaFactory,

)
from osf_tests.default_test_schema import DEFAULT_TEST_SCHEMA


@pytest.mark.django_db
class TestFileSchemaResponseDetail:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def url(self, schema_response):
        return f'/{API_BASE}files/{schema_response.parent._id}/schema_responses/{schema_response._id}/'

    @pytest.fixture
    def file_schema(self, user):
        return FileSchemaFactory(schema=DEFAULT_TEST_SCHEMA)

    @pytest.fixture
    def schema_response(self, user):
        return FileSchemaResponseFactory(initiator=user)

    def test_file_schema_response_detail(self, app, url, user, schema_response):
        '''
        DRAFT!
        '''
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema_response._id

        # test_authenticated_can_view_public_file_metadata_record
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema_response._id

        # test_unauthenticated_cannot_view_private_file_metadata_record
        res = app.get(url, expect_errors=True)
        assert res.status_code == 200

        # test_authenticated_can_view_private_file_metadata_record
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == schema_response._id

        # test_unauthorized_cannot_view_private_file_metadata_record
        unauth = AuthUserFactory()
        res = app.get(url, auth=unauth.auth, expect_errors=True)
        assert res.status_code == 200

        # test_cannot_delete_metadata_records
        res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405


@pytest.mark.django_db
class TestFileSchemaResponseUpdate:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    @pytest.fixture
    def user_read(self):
        return AuthUserFactory()

    @pytest.fixture
    def node(self, user, user_read):
        project = ProjectFactory(creator=user, is_public=True)
        project.add_contributor(user_read, permissions='read')
        return project

    @pytest.fixture
    def schema_response(self, user, node):
        return FileSchemaResponseFactory(initiator=user, parent=node)

    @pytest.fixture
    def url(self, schema_response):
        return f'/{API_BASE}files/{schema_response.parent._id}/schema_responses/{schema_response._id}/'

    @pytest.fixture
    def payload(self, schema_response):
        return {
            'data': {
                'id': schema_response._id,
                'type': 'file_schema_response',
                'attributes': {
                    'responses': {
                        'q1': 'You thought we was finished?!',
                        'q2': 'You ready?!',
                    }
                }
            }
        }

    def test_admin_can_update(self, app, user, node, url, schema_response, payload):
        res = app.patch_json_api(url, payload, auth=user.auth)
        schema_response.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['responses'] == {
            'q1': 'You thought we was finished?!',
            'q2': 'You ready?!',
        }
        assert schema_response.responses == {
            'q1': 'You thought we was finished?!',
            'q2': 'You ready?!',
        }
        assert node.logs.filter(action=NodeLog.FILE_SCHEMA_RESPONSE_UPDATED).exists()

    def test_write_can_update(self, app, url, schema_response, payload, user):
        res = app.patch_json_api(url, payload, auth=user.auth)
        schema_response.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['responses'] == {
            'q1': 'You thought we was finished?!',
            'q2': 'You ready?!',
        }
        assert schema_response.responses == {
            'q1': 'You thought we was finished?!',
            'q2': 'You ready?!',
        }

    def test_read_cannot_update(self, app, user_read, url, schema_response, payload):
        res = app.patch_json_api(url, payload, auth=user_read.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_fails_with_extra_key(self, app, user, url, schema_response, payload):
        payload['data']['attributes']['responses']['invalid_key'] = 'value'
        res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        schema_response.reload()
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Your response contained invalid keys: invalid_key'
        assert schema_response.responses == {}
