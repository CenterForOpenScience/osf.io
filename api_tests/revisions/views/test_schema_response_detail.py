import pytest

from osf_tests.factories import (
    SchemaResponsesFactory,
    RegistrationFactory,
    RegistrationSchemaFactory,
    AuthUserFactory
)

from django.contrib.contenttypes.models import ContentType
from osf.models import SchemaResponseBlock, SchemaResponses


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
            revision_justification='test justification',
            schema=schema
        )
        response_block = SchemaResponseBlock.objects.create(
            schema_key='q1',
            response={'value': 'initial value'},
            source_block=schema.schema_blocks.get(registration_response_key='q1'),
            source_revision=schema_response,
        )
        response_block.save()
        schema_response.response_blocks.add(response_block)

        response_block = SchemaResponseBlock.objects.create(
            schema_key='q2',
            response={'value': 'initial value'},
            source_block=schema.schema_blocks.get(registration_response_key='q2'),
            source_revision=schema_response,
        )
        response_block.save()
        schema_response.response_blocks.add(response_block)
        return schema_response

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_responses/{schema_response._id}/'

    def test_schema_response_detail(self, app, schema_response, user, url):
        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        schema_response.parent.add_contributor(user, 'read')
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id
        assert data['attributes']['revision_justification'] == schema_response.revision_justification
        assert data['attributes']['revision_response'] == [{'q1': {'value': 'initial value'}}, {'q2': {'value': 'initial value'}}]

        schema_response.parent.remove_permission(user, 'read', save=True)
        schema_response.parent.is_public = True
        schema_response.parent.save()
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200

    def test_schema_response_detail_update(self, app, schema_response, payload, user, url):
        resp = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        schema_response.parent.add_contributor(user, 'read')
        resp = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        schema_response.parent.add_contributor(user, 'write')
        resp = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id

        schema_response.refresh_from_db()
        assert schema_response.response_blocks.count() == 2
        block = schema_response.response_blocks.first()
        assert block.schema_key == 'q1'
        assert block.response == {'value': 'update value'}

    def test_schema_response_detail_revised_responses(self, app, schema_response, payload, user, url):
        revised_schema = SchemaResponses.create_from_previous_schema_response(
            schema_response.initiator,
            schema_response
        )
        revised_schema.parent.add_contributor(user, 'read')

        resp = app.get(f'/v2/schema_responses/{revised_schema._id}/', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema._id
        assert data['attributes']['revised_responses'] == []

        revised_schema.update_responses({'q1': {'value': 'update value'}, 'q2': {'value': 'initial value'}})
        resp = app.get(f'/v2/schema_responses/{revised_schema._id}/', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema._id
        assert data['attributes']['revised_responses'] == ['q1']

    def test_schema_response_detail_validation(self, app, schema_response, invalid_payload, user, url):
        schema_response.parent.add_contributor(user, 'admin')

        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'payload requires key: q1'

        invalid_payload['data']['attributes']['revision_response']['q1'] = {'test': 'new value'}
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Encountered unexpected keys: oops'
