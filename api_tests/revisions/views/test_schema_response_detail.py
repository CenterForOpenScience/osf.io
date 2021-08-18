import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)

from django.contrib.contenttypes.models import ContentType
from osf.models.schema_responses import SchemaResponseBlock


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
                        'q1': {'value': 'update value'},
                        'q2': {'value': 'initial value'},  # fake it out by adding an old value
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
        schema_response = SchemaResponsesFactory(
            content_type=content_type,
            object_id=node.id,
            initiator=node.creator,
            revision_justification='test justification'
        )
        response_block = SchemaResponseBlock.objects.create(
            schema_key='q1',
            response={'value': 'initial value'},
            source_block=node.registered_schema.first().schema_blocks.get(registration_response_key='q1'),
        )
        response_block.save()
        schema_response.response_blocks.add(response_block)

        response_block = SchemaResponseBlock.objects.create(
            schema_key='q2',
            response={'value': 'initial value'},
            source_block=node.registered_schema.first().schema_blocks.get(registration_response_key='q1'),
        )
        response_block.save()
        schema_response.response_blocks.add(response_block)
        return schema_response

    @pytest.fixture()
    def revised_response(self, node, schema, schema_response):
        content_type = ContentType.objects.get_for_model(node)
        return SchemaResponsesFactory(
            content_type=content_type,
            object_id=node.id,
            initiator=node.creator,
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
        assert data['attributes']['revision_response'] == [{'q1': {'value': 'initial value'}}, {'q2': {'value': 'initial value'}}]

    def test_schema_response_detail_update(self, app, schema_response, payload, user, url):
        resp = app.patch_json_api(url, payload, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id

        schema_response.refresh_from_db()
        assert schema_response.response_blocks.count() == 2
        block = schema_response.response_blocks.first()
        assert block.schema_key == 'q1'
        assert block.response == {'value': 'update value'}

    def test_schema_response_detail_get_revised_responses(self, app, revised_response, payload, user, url):
        resp = app.patch_json_api(
            f'/v2/revisions/{revised_response._id}/',
            payload,
            auth=user.auth
        )
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_response._id
        assert data['attributes']['revised_responses'] == ['q1']

        revised_response.refresh_from_db()
        assert revised_response.response_blocks.count() == 1
        block = revised_response.response_blocks.first()
        assert block.schema_key == 'q1'
        assert block.response == {'value': 'update value'}

    def test_schema_response_detail_validation(self, app, schema_response, invalid_payload, user, url):
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Schema Response key "oops" not found in schema "test schema"'
