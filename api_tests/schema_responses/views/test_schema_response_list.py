import pytest
from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)
from osf.migrations import update_provider_auth_groups
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
    update_provider_auth_groups()
    provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION
    provider.save()
    return provider


@pytest.fixture()
def url():
    return '/v2/schema_responses/'


def configure_auth(role, registration=None, schema_response=None):
    if role == 'unauthenticated':
        return None

    user = AuthUserFactory()
    if role == 'non-contributor':
        return user.auth

    registration = registration or schema_response.parent
    if role == 'moderator' and registration.provider is not None:
        registration.provider.get_group('moderator').user_set.add(user)
    else:
        registration.parent.add_contributor(user, role)

    return user.auth

@pytest.mark.django_db
class TestSchemaResponseListGETPermissions:
    '''Checks access for GET requests to the SchemaResponseList Endpoint.'''

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_status_code(self, app, url, perms_user, use_auth):
        resp = app.get(url, auth=AuthUserFactory().auth if use_auth else None)
        assert resp.status_code == 200

@pytest.mark.django_db
class TestSchemaResponseLsitGETBehavior:
    '''Tests the visibility of SchemaResponses through the List endpoint under various conditions.

    APPROVED SchemaResponses on public registrations should appear for all users.
    Only contributors (READ, WRITE, or ADMIN) should see non-APPROVED Schemaresponses or
    SchemaResponses for private registrations -- moderators have no special powers on this endpoint.
    SchemaResponses on deleted or withdrawn registrations should never appear.
    '''

    @pytest.fixture()
    def approved_schema_response(self, admin_user):
        '''A public schema_response'''
        parent = RegistrationFactory(creator=admin_user, is_public=True)
        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    @pytest.fixture(params=UNAPPROVED_RESPONSE_STATES)
    def unapproved_schema_response(self, approved_schema_response):
        return SchemaResponse.create_from_previous_response(
            previous_response=approved_schema_response,
            initiator=approved_schema_response.initiator
        )

    @pytest.fixture()
    def private_registration_response(self, admin_user):
        parent = RegistrationFactory(creator=admin_user, is_public=False)
        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response

    @pytest.fixture()
    def moderated_response(self, admin_user, provider):
        parent = RegistrationFactory(creator=admin_user, provider=provider, is_public=True)
        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        response.save()
        return response

    @pytest.fixture()
    def withdrawn_registration_response(self, admin_user):
        parent = RegistrationFactory(creator=admin_user, is_public=True)
        parent.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        parent.save()

        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state('APPROVED')
        response.save()
        return response

    @pytest.fixture()
    def deleted_registration_response(self):
        parent = RegistrationFactory(creator=admin_user)
        parent.deleted = timezone.now()
        parent.save()

        response = parent.schema_responses.last()
        response.approvals_state_machine.set_state('APPROVED')
        response.save()
        return response

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_unapproved_response_visibility(
            self, app, url, approved_response, unapproved_response, role):
        auth = configure_auth(unapproved_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {approved_response._id}
        if role in CONTRIBUTOR_ROLES:
            expected_ids.add(unapproved_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_private_registration_response_visibility(
            self, app, url, approved_response, private_registration_response, role):
        auth = configure_auth(private_registration_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {approved_response._id}
        if role in CONTRIBUTOR_ROLES:
            expected_ids.add(private_registration_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_moderated_response_visibility(
            self, app, url, approved_response, moderated_response, role):
        auth = configure_auth(moderated_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {approved_response._id}
        if role in CONTRIBUTOR_ROLES:
            expected_ids.add(moderated_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_withdrawn_registration_response_visibility(
            self, app, url, approved_response, withdrawn_registration_response, role):
        auth = configure_auth(withdrawn_registration_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {approved_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_contributor_cannot_see_deleted_registration_responses(
            self, app, url, approved_response, deleted_registration_response, role):
        auth = configure_auth(deleted_registration_response.parent, role)
        resp = app.get(url, auth=auth)

        expected_ids = {approved_response._id}
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids


@pytest.mark.django_db
class TestSchemaResponseListPOSTPermissions:
    '''Checks access for POST requests to the SchemaResponseList Endpoint.

    Only ADMIN users on the parent registration should be able to POST to SchemaResponseList.
    ADMIN users should be allowed to POST even if the parent registration is private, so
    long as other preconditions are not violated.
    '''

    @pytest.fixture()
    def registration(self, admin_user, provider):
        registration = RegistrationFactory(creator=admin_user, provider=provider)
        registration.moderation_state = RegistrationModerationStates.ACCEPTED.db_name
        registration.schema_responses.clear()  # Avoid conflicts arising from previous responses
        registration.save()
        return registration

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

    EXPECTED_CODE_FOR_ROLE = dict({role: 403 for role in USER_ROLES}, admin=201, unauthenticated=401)

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('is_public', [True, False])
    def test_status_code(self, app, url, registration, payload, role, is_public):
        auth = configure_auth(registration)
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
        auth = configure_auth(registration)
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
        auth = configure_auth(registration)
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
        return registration

    @pytest.fixture()
    def schema_response(self, registration):
        '''A pre-existing, APPROVED SchemaResponse on the registration.'''
        response = SchemaResponse.create_initial_response(
            parent=registration, initiator=registration.creator
        )
        response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        response.save()
        return response()

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

        created_response = registration.schema_responses.first()
        assert created_response._id == resp.json['data']['id']
        assert created_response.parent == registration
        assert created_response.schema == registration.registration_schema

    def test_post_with_previous_approved_response(
            self, app, url, registration, schema_response, payload, admin_user):
        resp = app.post_json_api(url, payload, auth=admin_user.auth)

        new_response = SchemaResponse.objects.get(_id=resp.json['data']['id'])
        assert new_response.previous_response == schema_response
        assert new_response.schema == schema_response.schema
        assert new_response == registration.schema_responses.first()

    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_cannot_post_if_non_approved_response(
            self, app, url, schema_response, payload, admin_user, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        resp = app.post_json_api(url, payload, auth=admin_user.auth, expect_errors=True)

        assert resp.status_code == 409

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
    '''Confirm that SchemaResponseList endpoint does not support PATCH, PUT, or DELETE methods.'''

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_patch(self, app, url, use_auth):
        resp = app.patch_json_api(
            url,
            auth=AuthUserFactory().auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_put(self, app, url, use_auth):
        resp = app.put_json_api(
            url,
            auth=AuthUserFactory().auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_delete_as_non_contributor(self, app, url, use_auth):
        resp = app.delete_json_api(
            url,
            auth=AuthUserFactory if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405
