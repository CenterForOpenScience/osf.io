import pytest

from osf_tests.factories import (
    RegistrationFactory,
    AuthUserFactory
)

from osf.models import SchemaResponse
from osf_tests.utils import DEFAULT_TEST_SCHEMA


@pytest.mark.django_db
class TestSchemaResponseDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'schema-responses',
                'attributes': {
                    'revision_response': {
                        'q1': {'value': 'update value'},
                        'q2': {'value': 'initial value'},  # fake it out by adding an old value
                    }
                }
            }
        }

    @pytest.fixture()
    def invalid_payload(self):
        return {
            'data': {
                'type': 'schema-responses',
                'attributes': {
                    'revision_response': {
                        'oops': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def url(self, registration):
        schema_response = registration.schema_responses.last()
        return f'/v2/schema_responses/{schema_response._id}/'

    def test_schema_response_detail(self, app, registration, user, url):
        schema_response = registration.schema_responses.get()

        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id
        assert data['attributes']['revision_justification'] == schema_response.revision_justification

        # default test schema
        assert data['attributes']['revision_responses'] == {
            'q1': '',
            'q2': '',
            'q3': '',
            'q4': '',
            'q5': schema_response.parent.visible_contributors.values_list('fullname', flat=True)[0],
            'q6': '',
        }

    def test_schema_response_detail_update(self, app, registration, user, payload, url):
        schema_response = registration.schema_responses.get()

        resp = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == schema_response._id

        schema_response.refresh_from_db()
        assert schema_response.response_blocks.count() == len([
            block for block in DEFAULT_TEST_SCHEMA['blocks'] if block.get('registration_response_key')
        ])
        block = schema_response.response_blocks.get(schema_key='q1')
        assert block.schema_key == 'q1'
        assert block.response == {'value': 'update value'}

    def test_schema_response_detail_revised_responses(self, app, registration, user, payload, url):
        schema_response = registration.schema_responses.get()

        revised_schema = SchemaResponse.create_from_previous_response(
            schema_response.initiator,
            schema_response
        )

        resp = app.get(f'/v2/schema_responses/{revised_schema._id}/', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema._id
        assert data['attributes']['updated_response_keys'] == []

        revised_schema.update_responses({'q1': {'value': 'update value'}, 'q2': ''})
        resp = app.get(f'/v2/schema_responses/{revised_schema._id}/', auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema._id
        assert data['attributes']['updated_response_keys'] == ['q1']

    def test_schema_response_detail_validation(self, app, invalid_payload, registration, user, url):
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert errors[0]['detail'] == 'Encountered unexpected keys: oops'

    def test_schema_response_detail_delete(self, app, registration, user, url):
        schema_response = registration.schema_responses.get()

        resp = app.delete_json_api(url, auth=user.auth)
        assert resp.status_code == 204

        with pytest.raises(SchemaResponse.DoesNotExist):  # shows it was really deleted
            schema_response.refresh_from_db()
