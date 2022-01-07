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
    def node(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture
    def schema_response(self, user):
        return FileSchemaResponseFactory(initiator=user)

    @pytest.fixture
    def url(self, schema_response):
        return f'/{API_BASE}files/{schema_response.parent._id}/schema_responses/{schema_response._id}/'

    @pytest.fixture
    def metadata_record_json(self):
        return {
            'file_description': 'Plot of change over time',
            'related_publication_doi': '10.1025/osf.io/abcde',
            'funders': [
                {'funding_agency': 'LJAF'},
                {'funding_agency': 'Templeton', 'grant_number': '12345'},
            ]
        }

    @pytest.fixture
    def make_payload(self, metadata_record_json):
        def payload(record, metadata=None, relationships=None):
            payload_data = {
                'data': {
                    'id': record._id,
                    'type': 'file_schema_response',
                    'attributes': {
                        'responses': metadata_record_json if not metadata else metadata
                    }
                }
            }
            if relationships:
                payload_data['data']['relationships'] = relationships

            return payload_data
        return payload

    def test_admin_can_update(self, app, user, node, url, schema_response, make_payload, metadata_record_json):
        res = app.patch_json_api(url, make_payload(schema_response), auth=user.auth)
        schema_response.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['responses'] == metadata_record_json
        assert schema_response.response == metadata_record_json
        assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    def test_write_can_update(self, app, url, schema_response, make_payload, user, metadata_record_json):
        res = app.patch_json_api(url, make_payload(schema_response), auth=user.auth)
        schema_response.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['responses'] == metadata_record_json
        assert schema_response.responses == metadata_record_json

    def test_read_cannot_update(self, app, user, url, schema_response, make_payload):
        res = app.patch_json_api(url, make_payload(schema_response), auth=user.auth, expect_errors=True)
        assert res.status_code == 403

    def test_update_fails_with_extra_key(self, app, user, url, schema_response, make_payload):
        payload = make_payload(schema_response)
        payload['data']['attributes']['responses']['cat'] = 'sterling'
        res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        schema_response.reload()
        assert res.status_code == 400
        assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
        assert res.json['errors'][0]['meta'].get('metadata_schema', None)
        assert schema_response.responses == {}

    def test_update_fails_with_invalid_json(self, app, user, url, schema_response, make_payload):
        payload = make_payload(schema_response)
        payload['data']['attributes']['responses']['related_publication_doi'] = 'dinosaur'
        res = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        schema_response.reload()
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Your response of dinosaur for the field related_publication_doi was invalid.'
        assert schema_response.responses == {}
