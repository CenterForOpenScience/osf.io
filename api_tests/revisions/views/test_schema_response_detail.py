import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)

from django.contrib.contenttypes.models import ContentType


@pytest.mark.django_db
class TestSchemaResponseDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def schema(self):
        return RegistrationSchemaFactory(name='test schema')

    @pytest.fixture()
    def node(self, schema):
        return RegistrationFactory(schema=schema)

    @pytest.fixture()
    def payload(self, node):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {

                    'revision_response': {
                        'q1': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def invalid_payload(self, node):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {
                    'revision_response': {
                        'oops': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def schema_response(self, node, schema):
        content_type = ContentType.objects.get_for_model(node)
        return SchemaResponsesFactory(
            content_type=content_type,
            object_id=node.id,
            initiator=node.creator,
            revision_justification='test justification'
        )

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/revisions/{schema_response._id}/'

    def test_schema_response_detail(self, app, schema_response, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id
        assert data['attributes']['revision_justification'] == schema_response.revision_justification
        assert data['attributes']['revision_response'] == []

    def test_schema_response_detail_update(self, app, schema_response, payload, user, url):
        resp = app.patch_json_api(url, payload, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id

        schema_response.refresh_from_db()
        assert schema_response.schema_responses.count() == 2
        block = schema_response.schema_responses.first()
        assert block.schema_key == 'q1'
        assert block.response == {'value': 'test'}

    def test_schema_response_detail_validation(self, app, schema_response, invalid_payload, user, url):
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Schema Response key "oops" not found in schema "test schema"'

        schema_response.refresh_from_db()
        assert schema_response.schema_responses.count() == 0