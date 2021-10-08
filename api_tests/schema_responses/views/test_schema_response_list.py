import pytest
from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates


USER_ROLES = ['read', 'write', 'admin', 'moderator', 'non-contributor', 'unauthenticated']
CONTRIBUTOR_ROLES = ['read', 'write', 'admin']

UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]


@pytest.fixture()
def admin_user():
    return AuthUserFactory()


@pytest.fixture()
def provider():
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION.value
    provider.allow_updates = True
    provider.save()
    return provider


@pytest.fixture()
def url():
    return '/v2/schema_responses/'


def configure_auth(registration, role):
    if role == 'unauthenticated':
        return None

    user = AuthUserFactory()
    if role == 'non-contributor':
        return user.auth

    if role == 'moderator' and registration.provider is not None:
        registration.provider.get_group('moderator').user_set.add(user)
    else:
        registration.add_contributor(user, role)

    return user.auth

@pytest.mark.django_db
class TestSchemaResponseListGETPermissions:
    '''Checks access for GET requests to the SchemaResponseList Endpoint.'''

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_status_code(self, app, url, use_auth):
        resp = app.get(url, auth=AuthUserFactory().auth if use_auth else None)
        assert resp.status_code == 200

@pytest.mark.django_db
class TestSchemaResponseListGETBehavior:
    '''Tests the visibility of SchemaResponses through the List endpoint under various conditions.

    APPROVED SchemaResponses on public registrations should appear for all users.
    Only contributors (READ, WRITE, or ADMIN) should see non-APPROVED SchemaResponses or
    SchemaResponses for private registrations -- moderators have no special powers on this endpoint.
    SchemaResponses on deleted or withdrawn registrations should never appear.
    '''

    @pytest.fixture()
    def control_response(self, admin_user):
        '''A public SchemaResponse to ensure is present for all requests'''
        parent = RegistrationFactory(creator=admin_user, is_public=True)
        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    @pytest.fixture()
    def test_response(self, admin_user):
        '''A SchemaResponse to configure per-test'''
        parent = RegistrationFactory(creator=admin_user, is_public=True)
        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    @pytest.mark.parametrize('role', USER_ROLES)
    def test_GET__unapproved_response_visibility(
            self, app, url, control_response, test_response, response_state, role):
        test_response.approvals_state_machine.set_state(response_state)
        test_response.save()

        auth = configure_auth(test_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {control_response._id}
        if role in CONTRIBUTOR_ROLES:
            expected_ids.add(test_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_GET__private_registration_response_visibility(
            self, app, url, control_response, test_response, role):
        test_registration = test_response.parent
        test_registration.is_public = False
        test_registration.save()

        auth = configure_auth(test_registration, role)
        resp = app.get(url, auth=auth)

        expected_ids = {control_response._id}
        if role in CONTRIBUTOR_ROLES:
            expected_ids.add(test_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('is_public', [True, False])
    def test_GET__moderated_response_visibility(
            self, app, url, control_response, test_response, provider, is_public):
        test_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        test_response.save()

        test_registration = test_response.parent
        test_registration.is_public = is_public
        test_registration.provider = provider
        test_registration.save()

        auth = configure_auth(test_registration, 'moderator')
        resp = app.get(url, auth=auth)

        expected_ids = {control_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_GET__withdrawn_registration_response_visibility(
            self, app, url, control_response, test_response, role):
        test_registration = test_response.parent
        test_registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        test_registration.save()

        auth = configure_auth(test_registration, role)
        resp = app.get(url, auth=auth)

        expected_ids = {control_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_GET__deleted_registration_response_visibility(
            self, app, url, control_response, test_response, role):
        test_registration = test_response.parent
        test_registration.deleted = timezone.now()
        test_registration.save()

        auth = configure_auth(test_registration, role)
        resp = app.get(url, auth=auth)

        expected_ids = {control_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids


@pytest.mark.django_db
class TestSchemaResponseListPOSTPermissions:
    '''Checks access for POST requests to the SchemaResponseList Endpoint.'''

    @pytest.fixture()
    def registration(self, admin_user, provider):
        registration = RegistrationFactory(creator=admin_user, provider=provider)
        registration.moderation_state = RegistrationModerationStates.ACCEPTED.db_name
        registration.schema_responses.clear()  # Avoid conflicts arising from previous responses
        registration.save()
        provider = registration.provider
        provider.allow_updates = True
        provider.save()
        return registration

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'schema-responses',
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

    EXPECTED_CODE_FOR_ROLE = dict({role: 403 for role in USER_ROLES}, admin=201, unauthenticated=401)

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('is_public', [True, False])
    def test_status_code(self, app, url, registration, payload, role, is_public):
        auth = configure_auth(registration, role)
        registration.is_public = is_public
        registration.save()

        resp = app.post_json_api(
            url,
            payload,
            auth=auth,
            expect_errors=True
        )
        assert resp.status_code == self.EXPECTED_CODE_FOR_ROLE[role]

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_registration(self, app, url, registration, payload, role):
        auth = configure_auth(registration, role)
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.post_json_api(
            url,
            payload,
            auth=auth,
            expect_errors=True
        )
        assert resp.status_code == 401 if role == 'unauthenticated' else 403

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_registration(self, app, url, registration, payload, role):
        auth = configure_auth(registration, role)
        registration.deleted = timezone.now()
        registration.save()

        resp = app.post_json_api(
            url,
            payload,
            auth=auth,
            expect_errors=True
        )
        assert resp.status_code == 410


@pytest.mark.django_db
class TestSchemaResponseListPOSTBehavior:
    '''Tests for the POST method on the top-level SchemaResponseList endpoint.

    The create payload must include the relationship to the registration and must
    not include any unexpected data. The parent registration must not already have
    a SchemaResponse that is in-progress or pending approval.
    '''

    @pytest.fixture()
    def registration(self, admin_user):
        registration = RegistrationFactory(creator=admin_user)
        registration.moderation_state = RegistrationModerationStates.ACCEPTED.db_name
        registration.schema_responses.clear()
        registration.save()
        provider = registration.provider
        provider.allow_updates = True
        provider.save()
        return registration

    @pytest.fixture()
    def schema_response(self, registration):
        '''A pre-existing, APPROVED SchemaResponse on the registration.'''
        response = SchemaResponse.create_initial_response(
            parent=registration, initiator=registration.creator
        )
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    @pytest.fixture()
    def payload(self, registration):
        return {
            'data': {
                'type': 'schema-responses',
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
                'type': 'schema-responses'
            }
        }

    @pytest.fixture()
    def invalid_payload(self, registration):
        return {
            'data': {
                'type': 'schema-responses',
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

    def test_POST_creates_response(self, app, url, registration, payload, admin_user):
        assert not registration.schema_responses.exists()
        resp = app.post_json_api(url, payload, auth=admin_user.auth)

        registration.refresh_from_db()
        assert registration.schema_responses.count() == 1

        created_response = registration.schema_responses.first()
        assert created_response._id == resp.json['data']['id']
        assert created_response.parent == registration
        assert created_response.schema == registration.registration_schema
        assert created_response.state is ApprovalStates.IN_PROGRESS

    def test_POST_with_previous_approved_response(
            self, app, url, registration, schema_response, payload, admin_user):
        resp = app.post_json_api(url, payload, auth=admin_user.auth)

        new_response = SchemaResponse.objects.get(_id=resp.json['data']['id'])
        assert new_response.previous_response == schema_response
        assert new_response.schema == schema_response.schema
        assert new_response == registration.schema_responses.first()

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_POST_fails_with_prior_non_approved_response(
            self, app, url, schema_response, payload, admin_user, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)

        assert resp.status_code == 409

    def test_POST_fails_if_registration_relationship_not_in_payload(
            self, app, url, no_relationship_payload, admin_user):
        resp = app.post_json_api(url, no_relationship_payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 400

    def test_POST_fails_if_incorrect_relationship_type_in_payload(
            self, app, url, registration, invalid_payload, admin_user):
        resp = app.post_json_api(url, invalid_payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 400

    def test_POST_fails_for_nested_registration(self, app, url, registration, payload, admin_user):
        nested_registration = RegistrationFactory(
            project=ProjectFactory(parent=registration.registered_from, creator=admin_user),
            parent=registration,
            creator=admin_user
        )
        payload['data']['relationships']['registration']['data']['id'] = nested_registration._id
        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 409

    def test_POST_fails_if_provider_does_not_allow_updates(
            self, app, url, registration, payload, admin_user):
        provider = registration.provider
        provider.allow_updates = False
        provider.save()

        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)
        assert resp.status_code == 409


@pytest.mark.django_db
class TestSchemaResponseListUnsupportedMethods:
    '''Confirm that SchemaResponseList endpoint does not support PATCH, PUT, or DELETE methods.'''

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_PATCH(self, app, url, use_auth):
        resp = app.patch_json_api(
            url,
            auth=AuthUserFactory().auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_PUT(self, app, url, use_auth):
        resp = app.put_json_api(
            url,
            auth=AuthUserFactory().auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_DELETE(self, app, url, use_auth):
        resp = app.delete_json_api(
            url,
            auth=AuthUserFactory if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405
