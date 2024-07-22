import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)

USER_ROLES = ['read', 'write', 'admin', 'moderator', 'non-contributor', 'unauthenticated']
UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
DEFAULT_REVIEWS_WORKFLOW = ModerationWorkflows.PRE_MODERATION.value


def make_api_url(registration):
    return f'/v2/registrations/{registration._id}/schema_responses/'


def configure_test_preconditions(
        registration_status='public',
        moderator_workflow=DEFAULT_REVIEWS_WORKFLOW,
        updated_response_state=None,
        role='admin'):
    '''Create and Configure a RegistrationProvider, Registration, SchemaResponse, and User.'''
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = moderator_workflow
    provider.save()

    registration = RegistrationFactory(provider=provider)
    if registration_status == 'public':
        registration.is_public = True
    elif registration_status == 'private':
        registration.is_public = False
        # set moderation state to a realistic value for a private
        # registration with an approved response
        registration.moderation_state = 'embargo'
    elif registration_status == 'withdrawn':
        registration.moderation_state = 'withdrawn'
    elif registration_status == 'deleted':
        registration.deleted = timezone.now()
    registration.save()

    initial_response = registration.schema_responses.last()
    initial_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    initial_response.save()

    updated_response = None
    if updated_response_state is not None:
        updated_response = SchemaResponse.create_from_previous_response(
            previous_response=initial_response, initiator=initial_response.initiator
        )
        updated_response.approvals_state_machine.set_state(updated_response_state)
        updated_response.save()

    auth = configure_auth(registration, role)
    return auth, updated_response, registration, provider


def configure_auth(registration, role):
    '''Create a user and assign appropriate permissions for the given role.'''
    if role == 'unauthenticated':
        return None

    user = AuthUserFactory()
    if role == 'moderator':
        registration.provider.get_group('moderator').user_set.add(user)
    elif role == 'non-contributor':
        pass
    else:
        registration.add_contributor(user, role)

    return user.auth


@pytest.mark.django_db
class TestRegistrationSchemaResponseListGETPermissions:
    '''Checks access for GET requests to the RegistrationSchemaResponseList Endpoint.'''

    def _get_status_code_for_preconditions(self, registration_status, moderator_workflow, role):
        # Deleted registrations always return GONE
        if registration_status == 'deleted':
            return 410
        # Withdrawn registrations always return
        # UNAUTHORIZED for unauthenticated users and
        # FORBIDDEN for all othrs
        if registration_status == 'withdrawn':
            if role == 'unauthenticated':
                return 401
            return 403

        # All users can see SchemaResponses on public registrations
        # All contributors can see SchemaResponses on private registrations
        if registration_status == 'public' or role in ['read', 'write', 'admin']:
            return 200

        # Moderators can see (a subset) of SchemaResponses on moderated registrations
        if moderator_workflow is not None and role == 'moderator':
            return 200

        # Unauthenticated/non-contributors (including moderators on non-moderated registrations)
        # receive UNAUTHORIZED or FORBIDDEN, respectively, in all other cases
        if role == 'unauthenticated':
            return 401
        return 403

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('moderator_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code(self, app, registration_status, moderator_workflow, role):
        auth, _, registration, _ = configure_test_preconditions(
            registration_status=registration_status,
            moderator_workflow=moderator_workflow,
            role=role
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status=registration_status,
            moderator_workflow=moderator_workflow,
            role=role
        )

        resp = app.get(make_api_url(registration), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_registration(self, app, role):
        auth, _, registration, _ = configure_test_preconditions(
            registration_status='deleted',
            role=role
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status='deleted',
            moderator_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role
        )

        resp = app.get(make_api_url(registration), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_registration(self, app, role):
        auth, _, registration, _ = configure_test_preconditions(
            registration_status='withdrawn',
            role=role
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status='withdrawn',
            moderator_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role
        )

        resp = app.get(make_api_url(registration), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    def test_nested_registration_does_not_use_parent_permissions(self, app):
        auth, _, root_registration, _ = configure_test_preconditions(role='read')
        universal_admin = root_registration.creator

        nested_registration = RegistrationFactory(
            project=ProjectFactory(parent=root_registration.registered_from),
            parent=root_registration,
            user=universal_admin,
            is_public=False
        )

        # read user on parent shouldn't be able to GET SchemaResponses from child
        resp = app.get(make_api_url(nested_registration), auth=auth, expect_errors=True)
        assert resp.status_code == 403


@pytest.mark.django_db
class TestRegistrationSchemaResponseListGETBehavior:
    '''Test the results from GET requests against the RegistrationSchemaResponse endpoint.

    Contributors on the base Registration should be able to see all SchemaResponses
    on a registration, whether approved or not, for both public and private Registrations.

    Moderators should be able to see both PENDING_MODERATION and APPROVED SchemaResponses
    on Registrations that are part of the moderated provider.

    Non-contributors should only see APPROVED SchemaResponses on Public registrations
    (permissions tests verify 403/401 response for non-contributors on a private registration).
    '''

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_GET__public_registration_with_unapproved_response(self, app, role, response_state):
        auth, updated_response, registration, _ = configure_test_preconditions(
            registration_status='public',
            moderator_workflow=None,
            updated_response_state=response_state,
            role=role
        )
        resp = app.get(make_api_url(registration), auth=auth)

        # Always expect the APPROVED response
        expected_ids = {updated_response.previous_response._id}
        if role in ['read', 'write', 'admin']:
            expected_ids.add(updated_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    # Only test contributors here.
    # Moderators tested elsehwere, and permissions tests confirm that unauthenticated users
    # and non-contributors cannot GET SchemaResponses for private registrations
    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', ApprovalStates)
    def test_GET__private_registration_responses_as_contributor(self, app, role, response_state):
        auth, updated_response, registration, _ = configure_test_preconditions(
            registration_status='private',
            updated_response_state=response_state,
            role=role
        )
        resp = app.get(make_api_url(registration), auth=auth)

        expected_ids = set(registration.schema_responses.values_list('_id', flat=True))
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('response_state', ApprovalStates)
    def test_GET__moderated_registration_responses_as_moderator(
            self, app, registration_status, response_state):
        auth, updated_response, registration, _ = configure_test_preconditions(
            registration_status=registration_status,
            moderator_workflow=ModerationWorkflows.PRE_MODERATION.value,
            updated_response_state=response_state,
            role='moderator'
        )
        resp = app.get(make_api_url(registration), auth=auth)

        # Always expect the APPROVED response
        expected_ids = {updated_response.previous_response._id}
        if response_state in [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]:
            expected_ids.add(updated_response._id)
        encountered_ids = {entry['id'] for entry in resp.json['data']}
        assert encountered_ids == expected_ids

    def test_GET__nested_registration_returns_root_responses(self, app):
        root_registration = RegistrationFactory()
        admin = root_registration.creator

        nested_registration = RegistrationFactory(
            project=ProjectFactory(parent=root_registration.registered_from),
            parent=root_registration,
            user=admin
        )

        assert root_registration.schema_responses.exists()
        assert not nested_registration.schema_responses.exists()

        resp = app.get(make_api_url(nested_registration), auth=admin.auth)
        data = resp.json['data']

        encountered_ids = {entry['id'] for entry in data}
        assert encountered_ids == {root_registration.schema_responses.get()._id}


@pytest.mark.django_db
class TestRegistrationSchemaResponseListUnsupportedMethods:
    '''Make sure that RegistrationSchemaResponseList does not support POST, PUT, PATCH or DELETE.'''

    @pytest.fixture
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def url(self, registration):
        return f'/v2/registrations/{registration._id}/schema_responses/'

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_POST(self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.post_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PATCH(self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.patch_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PUT(self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.put_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_DELETE(self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.delete_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405
