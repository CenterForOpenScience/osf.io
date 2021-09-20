import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows

from osf.migrations import update_provider_auth_groups
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from osf_tests.factories import (
    # SchemaResponseFactory,
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)

USER_ROLES = ['read', 'write', 'admin', 'moderator', 'non-contributor', 'unauthenticated']
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
    provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION.value
    provider.save()
    return provider

@pytest.fixture()
def perms_user():
    return AuthUserFactory()


@pytest.fixture()
def registration(admin_user, provider):
    return RegistrationFactory(creator=admin_user, provider=provider)


@pytest.fixture()
def approved_response(registration, admin_user):
    response = registration.schema_responses.last()
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    return response


@pytest.fixture()
def non_approved_response(approved_response, admin_user):
    return SchemaResponse.create_from_previous_response(
        previous_response=approved_response,
        initiator=admin_user
    )


def configure_test_preconditions(
        registration,
        registration_status='public',
        moderator_workflow=ModerationWorkflows.PRE_MODERATION.value):
    '''Configure a given Registration and return a user with appropraite auth.'''
    provider = registration.provider
    provider.reviews_workflow = moderator_workflow
    provider.save()

    registration = RegistrationFactory(provider=provider)
    if registration_status == 'public':
        registration.is_public = True
    elif registration_status == 'private':
        registration.is_public = False
    elif registration_status == 'withdrawn':
        registration.moderation_state = 'withdrawn'
    elif registration_status == 'deleted':
        registration.deleted = timezone.now()
    registration.save()


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

@pytest.fixture()
def url(registration):
    return f'/v2/registrations/{registration._id}/schema_responses/'

@pytest.mark.django_db
class TestRegistrationsSchemaResponseListGETPermissions:
    '''Checks the status code for the GET requests to the RegistrationSchemaResponseList Endpoint.

    All users should be able to GET the SchemaResponseList for public registrations, while only
    contributors should be able to GET the SchemaResponseList for private registrations.

    Deleted and withdrawn registrations should return 410 and 403, respectively, when
    trying to GET the SchemaResponseList,
    '''

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
    def test_status_code(
            self, app, url, registration, registration_status, moderator_workflow, role):
        configure_test_preconditions(
            registration=registration,
            registration_status=registration_status,
            moderator_workflow=moderator_workflow
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status=registration_status,
            moderator_workflow=moderator_workflow,
            role=role
        )

        auth = configure_auth(registration, role)
        resp = app.get(url, auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_registration(self, app, url, registration, role):
        configure_test_preconditions(
            registration=registration,
            registration_status='deleted',
            moderator_workflow=ModerationWorkflows.PRE_MODERATION.value
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status='deleted',
            moderator_workflow=ModerationWorkflows.PRE_MODERATION.value,
            role=role
        )

        auth = configure_auth(registration, role)
        resp = app.get(url, auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_registration(self, app, url, registration, role):
        configure_test_preconditions(
            registration=registration,
            registration_status='withdrawn',
            moderator_workflow=ModerationWorkflows.PRE_MODERATION.value
        )
        expected_code = self._get_status_code_for_preconditions(
            registration_status='withdrawn',
            moderator_workflow=ModerationWorkflows.PRE_MODERATION.value,
            role=role
        )

        auth = configure_auth(registration, role)
        resp = app.get(url, auth=auth, expect_errors=True)
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestRegistrationSchemaResponseListGETBehavior:
    '''Test the results from GET requests against the RegistrationSchemaResponse endpoint.

    Contributors on the base Registration should be able to see all SchemaResponses
    on a registration, whether approved or not, whether the Registration is public
    or private.

    Non-contributors should only see APPROVED SchemaResponses on Public registrations
    (permissions tests verify 403/401 response for non-contributors on a private registration).
    '''

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_GET__public_registration_with_unapproved_response(
            self, app, url, registration, non_approved_response, role, response_state):
        registration.is_public = True
        registration.save()

        non_approved_response.approvals_state_machine.set_state(response_state)
        non_approved_response.save()

        auth = configure_auth(registration, role)
        resp = app.get(url, auth=auth)

        expected_ids = registration.schema_responses.last()._id
        if role in ['read', 'write', 'admin']:
            expected_ids.add(non_approved_response._id)
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_GET__private_registration_with_unapproved_response(
            self, app, url, registration, non_approved_response, role, response_state):
        registration.is_public = True
        registration.save()

        non_approved_response.approvals_state_machine.set_state(response_state)
        non_approved_response.save()

        auth = configure_auth(registration, role)
        resp = app.get(url, auth=auth)

        expected_ids = set(registration.schema_responses.values_list('_id', flat=True))
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('is_public', [True, False])
    @pytest.mark.parametrize('response_state', ApprovalStates)
    def test_GET__moderated_registration_with_unapproved_response(
            self, app, url, registration, non_approved_response, is_public, response_state):
        registration.is_public = True
        registration.save()

        provider = registration.provider
        provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION.value
        provider.save()

        non_approved_response.approvals_state_machine.set_state(response_state)
        non_approved_response.save()

        auth = configure_auth(registration, 'moderator')
        resp = app.get(url, auth=auth)

        expected_ids = {registration.schema_responses.last()._id}
        if response_state in [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]:
            expected_ids.add(non_approved_response._id)
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids


@pytest.mark.django_db
class TestRegistrationSchemaResponseListUnsupportedMethods:
    '''Make sure that RegistrationSchemaResponseList does not support POST, PUT, PATCH or DELETE.'''

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_POST(
            self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.post_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PATCH(
            self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.patch_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PUT(
            self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.put_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_DELETE(
            self, app, url, registration, role):
        auth = configure_auth(registration, role)
        resp = app.delete_json_api(url, auth=auth, expect_errors=True)
        assert resp.status_code == 405
