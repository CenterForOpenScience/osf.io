import pytest

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    SchemaResponseFactory
)

from osf.models import SchemaResponse
from osf_tests.utils import DEFAULT_TEST_SCHEMA, get_default_test_schema
from osf.utils.workflows import ApprovalStates

@pytest.mark.django_db
class TestSchemaResponseDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory(schema=get_default_test_schema())

    @pytest.fixture()
    def schema_response(self, registration):
        return registration.schema_responses.get()

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {
                    'revision_responses': {
                        'q1': 'update value',
                        'q2': 'initial value',  # fake it out by adding an old value
                    }
                }
            }
        }

    @pytest.fixture()
    def invalid_payload(self):
        return {
            'data': {
                'type': 'schema_responses',
                'attributes': {
                    'revision_responses': {
                        'oops': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_responses/{schema_response._id}/'

    def test_schema_response_detail(self, app, schema_response, url):
        schema_response.parent.is_public = True
        schema_response.parent.save()
        resp = app.get(url)
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
            'q5': '',
            'q6': '',
        }

    def test_schema_response_detail_revised_responses(self, app, registration, schema_response, payload, url):
        revised_schema_response = SchemaResponseFactory(
            registration=registration
        )

        schema_response.parent.is_public = True
        schema_response.parent.save()
        resp = app.get(f'/v2/schema_responses/{revised_schema_response._id}/')
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema_response._id
        assert data['attributes']['updated_response_keys'] == []

        revised_schema_response.update_responses({'q1': 'update value', 'q2': None})
        resp = app.get(f'/v2/schema_responses/{revised_schema_response._id}/')
        assert resp.status_code == 200
        data = resp.json['data']
        assert data['id'] == revised_schema_response._id
        assert data['attributes']['updated_response_keys'] == ['q1']

    def test_schema_response_detail_update(self, app, schema_response, user, payload, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        schema_response.parent.add_contributor(user, 'write')
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
        assert block.response == 'update value'

    def test_schema_response_detail_validation(self, app, invalid_payload, schema_response, user, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        schema_response.parent.add_contributor(user, 'write')
        resp = app.patch_json_api(url, invalid_payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 400
        errors = resp.json['errors']
        assert len(errors) == 1
        assert 'oops' in errors[0]['detail']

    def test_schema_response_detail_delete(self, app, schema_response, user, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        schema_response.parent.add_contributor(user, 'admin')
        resp = app.delete_json_api(url, auth=user.auth)
        assert resp.status_code == 204

        with pytest.raises(SchemaResponse.DoesNotExist):  # shows it was really deleted
            schema_response.refresh_from_db()

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 403, ),  # assumes private registration
            ('read', 200, ),
            ('write', 200, ),
            ('admin', 200, ),
        ]
    )
    def test_schema_response_auth_get(self, app, schema_response, payload, permission, user, expected_response, url):
        if permission:
            schema_response.parent.add_contributor(user, permission)
        resp = app.get(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_auth_post(self, app, schema_response, payload, permission, user, expected_response, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        if permission:
            schema_response.parent.add_contributor(user, permission)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 403, ),
            ('read', 403, ),
            ('write', 200, ),
            ('admin', 200, ),
        ]
    )
    def test_schema_response_auth_patch(self, app, schema_response, payload, permission, user, expected_response, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        if permission:
            schema_response.parent.add_contributor(user, permission)
        resp = app.patch_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 403, ),
            ('read', 403, ),
            ('write', 403, ),
            ('admin', 204, ),
        ]
    )
    def test_schema_response_auth_delete(self, app, schema_response, payload, permission, user, expected_response, url):
        schema_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        schema_response.save()
        if permission:
            schema_response.parent.add_contributor(user, permission)
        resp = app.delete_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response
