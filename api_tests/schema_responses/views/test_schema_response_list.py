import pytest

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    SchemaResponseFactory,
)

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates


UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
UNSUPPORTED_REGISTRATION_STATES = [
    state for state in RegistrationModerationStates
    if state not in {RegistrationModerationStates.ACCEPTED, RegistrationModerationStates.EMBARGO}
]

@pytest.fixture()
def perms_user():
    return AuthUserFactory()

@pytest.fixture()
def admin_user():
    return AuthUserFactory()

@pytest.fixture()
def url():
    return '/v2/schema_responses/'


@pytest.mark.django_db
class TestSchemaResponseListGETPermissions:
    '''Checks the status code for the GET requests to the SchemaResponseList Endpoint.

    All users should be able to call GET without receiving an error, the difference
    should be in the resulting queryset.
    '''

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_status_code(self, app, url, perms_user, use_auth):
        resp = app.get(url, auth=perms_user.auth if use_auth else None, expect_errors=True)
        assert resp.status_code == 200

@pytest.mark.django_db
class TestSchemaResponseLsitGETBehavior:
    '''Tests the visibility of SchemaResponses through the List endpoint under various conditions.

    All users should be able to see APPROVED responses on (non-withdrawn) public registrations.
    No users should be able to see responses on WITHDRAWN registrations
    Only contributors should be able to see non-APPROVED responses on public registrations.
    Only contributors should be able to see responses on private registrations.
    '''

    @pytest.fixture()
    def public_registration(self, admin_user):
        '''A public registration'''
        registration = RegistrationFactory(creator=admin_user)
        registration.is_public = True
        registration.save()
        return registration

    @pytest.fixture()
    def approved_schema_response(self, public_registration):
        '''A public schema_response'''
        response = SchemaResponseFactory(
            registration=public_registration,
            initiator=public_registration.creator,
        )
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    # Tests will also inherit approved_schema_response, public_registration, and admin_user
    @pytest.fixture(autouse=True)
    def unapproved_schema_response(self, approved_schema_response):
        return SchemaResponse.create_from_previous_response(
            previous_response=approved_schema_response,
            initiator=approved_schema_response.initiator
        )

    @pytest.fixture()
    def private_registration(self, admin_user):
        return RegistrationFactory(creator=admin_user)

    # Tests will also inherit private_registration
    @pytest.fixture(autouse=True)
    def private_schema_response(self, private_registration):
        response = SchemaResponse.create_initial_response(
            parent=private_registration,
            initiator=private_registration.creator
        )
        response.approvals_state_machine.set_state('APPROVED')
        response.save()
        return response

    @pytest.fixture()
    def withdrawn_registration(self, admin_user):
        registration = RegistrationFactory(creator=admin_user)
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()
        return registration

    # Tests will also inherit withdrawn_registration
    @pytest.fixture(autouse=True)
    def withdrawn_schema_response(self, withdrawn_registration):
        response = SchemaResponse.create_initial_response(
            parent=withdrawn_registration,
            initiator=withdrawn_registration.creator
        )
        response.approvals_state_machine.set_state('APPROVED')
        response.save()
        return response

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    @pytest.mark.parametrize('use_auth', [True, False])
    def test_non_contributor_response_visibility(
            self, app, url, approved_schema_response, unapproved_schema_response, perms_user, response_state, use_auth):
        unapproved_schema_response.approvals_state_machine.set_state(response_state)
        unapproved_schema_response.save()

        resp = app.get(url, auth=perms_user.auth if use_auth else None, expect_errors=True)

        # non-contributor/non-logged-in user should not get results for the
        # non-approved response, the private registration, or the withdrawn registration
        expected_ids = {approved_schema_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_contributor_can_see_unapproved_responses(
            self, app, url, public_registration, approved_schema_response, unapproved_schema_response, perms_user, response_state, role):
        unapproved_schema_response.approvals_state_machine.set_state(response_state)
        unapproved_schema_response.save()
        public_registration.add_contributor(perms_user, role)
        resp = app.get(url, auth=perms_user.auth, expect_errors=True)

        expected_ids = {approved_schema_response._id, unapproved_schema_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_contributor_can_see_private_registration_responses(
            self, app, url, approved_schema_response, private_registration, private_schema_response, perms_user, role):
        private_registration.add_contributor(perms_user, role)
        resp = app.get(url, auth=perms_user.auth, expect_errors=True)

        expected_ids = {approved_schema_response._id, private_schema_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_contributor_cannot_see_withdrawn_registration_responses(
            self, app, url, approved_schema_response, withdrawn_registration, perms_user, role):
        withdrawn_registration.add_contributor(perms_user, role)
        resp = app.get(url, auth=perms_user.auth, expect_errors=True)

        expected_ids = {approved_schema_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids


@pytest.mark.django_db
class TestSchemaResponseListPOSTPermissions:
    '''Checks the status code for the POST requests to the SchemaResponseList Endpoint.

    Only ADMIN users on the parent registration should be able to POST to SchemaResponseList.
    ADMIN users should be allowed to POST even if the parent registration is private, so
    long as other preconditions are not violated.
    '''

    @pytest.fixture()
    def registration(self, admin_user):
        return RegistrationFactory(creator=admin_user)

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'revisions',
                'relationships': {
                    'registration': {
                        'data': {
                            'id': registration._id,
                            'type': 'registrations'
                        }
                    }
                }
            }
        }

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 403), ('admin', 201)])
    @pytest.mark.parametrize('is_public', [True, False])
    def test_response_code_as_non_contributor(
            self, app, url, registration, payload, perms_user, role, is_public, expected_code):
        registration.add_contributor(perms_user, role)
        registration.is_public = is_public
        registration.save()

        resp = app.post_json_api(
            url,
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    @pytest.mark.parametrize('is_public', [True, False])
    def test_response_code_as_contributor(
            self, app, url, registration, payload, perms_user, use_auth, is_public):
        registration.is_public = is_public
        registration.save()

        resp = app.post_json_api(
            url,
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

@pytest.mark.django_db
class TestSchemaResponseListPOST:
    '''Tests for the POST method on the top-level SchemaResponseList endpoint.

    Only admin users on the registration associated with the SchemaResponse should
    be able to call POST. All other logged-in users should get a 403, while
    non-logged in users should get a 401. This is true for both public and private
    registrations.

    The create payload must include the relationship to the registration and must
    not include any unexpected data.

    New SchemaResponses cannot be created on a Registration that has not been
    approved or that already has a non-approved SchemaResponse
    '''
    @pytest.fixture()
    def registration(self, admin_user):
        return RegistrationFactory(creator=admin_user)

    @pytest.fixture()
    def schema_response(self, registration):
        '''An pre-existing schema_response on the registration.'''
        return SchemaResponse.create_initial_response(
            parent=registration,
            initiator=registration.creator
        )

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'revisions',
                'relationships': {
                    'registration': {
                        'data': {
                            'id': registration._id,
                            'type': 'registrations'
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def no_relationship_payload(self):
        return {
            'data': {
                'type': 'revisions'
            }
        }

    @pytest.fixture()
    def invalid_payload(self, registration):
        return {
            'data': {
                'type': 'revisions',
                'relationships': {
                    'registration': {
                        'data': {
                            'id': registration._id,
                            'type': 'not yours',
                            'rogue_property': 'dsdas'
                        }
                    }
                }
            }
        }

    def test_post_creates_response(self, app, url, registration, payload, admin_user):
        assert not registration.schema_responses.exists()
        resp = app.post_json_api(url, payload, auth=admin_user.auth)

        registration.refresh_from_db()
        assert registration.schema_responses.count() == 1
        assert registration.schema_responses.first()._id == resp.json['data']['id']

    def test_post_with_previous_approved_response(
            self, app, url, registration, schema_response, payload, admin_user):
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()
        resp = app.post_json_api(url, payload, auth=admin_user.auth)

        new_response = SchemaResponse.objects.get(_id=resp.json['data']['id'])
        assert new_response.previous_response == schema_response
        assert new_response in registration.schema_responses.all()

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_cannot_post_if_non_approved_response(
            self, app, url, schema_response, payload, admin_user, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)

        assert resp.status_code == 400

    @pytest.mark.parametrize('registration_state', UNSUPPORTED_REGISTRATION_STATES)
    def test_cannot_post_if_invalid_registration_state(
            self, app, url, registration, payload, admin_user, registration_state):
        registration.moderation_state = registration_state.db_name
        registration.save()
        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)

        assert resp.status_code == 400

    def test_cannot_post_payload_without_registration_relationship(
            self, app, url, no_relationship_payload, admin_user):
        resp = app.post_json_api(url, no_relationship_payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 400
        print(resp.json['errors'][0]['detail'])

    def test_cannot_post_payload_with_incorrect_relationship_type(
            self, app, url, registration, invalid_payload, admin_user):
        resp = app.post_json_api(url, invalid_payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 400
        assert "'not yours' does not match 'registrations'\n\nFailed validating 'pattern'" in resp.json['errors'][0]['detail']


@pytest.mark.django_db
class TestSchemaResponseListUnsupportedMethods:

    @pytest.fixture()
    def registration(self, admin_user):
        return RegistrationFactory(creator=admin_user)

    @pytest.fixture()
    def schema_response(self, registration):
        '''An unapproved schema_response on the registration.'''
        return SchemaResponse.create_initial_response(
            parent=registration,
            initiator=registration.creator
        )

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'revisions',
                'relationships': {
                    'registration': {
                        'data': {
                            'id': registration._id,
                            'type': 'registrations'
                        }
                    }
                }
            }
        }

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    def test_patch_response_code_with_auth(self, app, url, registration, payload, perms_user, role):
        if role:
            registration.add_contributor(perms_user, role)
        resp = app.patch_json_api(url, payload, auth=perms_user.auth, expect_errors=True)
        assert resp.status_code == 405

    def test_patch_response_code_no_auth(self, app, url, registration, payload):
        resp = app.patch_json_api(url, payload, auth=None, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    def test_delete_response_code_with_auth(
            self, app, url, registration, payload, perms_user, role):
        if role:
            registration.add_contributor(perms_user, role)
        resp = app.delete_json_api(url, payload, auth=perms_user.auth, expect_errors=True)
        assert resp.status_code == 405

    def test_delete_response_code_no_auth(self, app, url, registration, payload):
        resp = app.delete_json_api(url, payload, auth=None, expect_errors=True)
        assert resp.status_code == 405
