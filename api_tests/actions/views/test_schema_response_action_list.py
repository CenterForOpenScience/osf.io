import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows

from osf.migrations import update_provider_auth_groups
from osf.utils.workflows import ApprovalStates
from osf.utils.workflows import SchemaResponseTriggers as Triggers

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)


USER_ROLES = ['read', 'write', 'admin', 'moderator', 'non-contributor', 'unauthenticated']
UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
DEFAULT_REVIEWS_WORKFLOW = ModerationWorkflows.PRE_MODERATION.value
DEFAULT_SCHEMA_RESPONSE_STATE = ApprovalStates.APPROVED
DEFAULT_TRIGGER = Triggers.SUBMIT


def make_api_url(schema_response):
    return f'/v2/schema_responses/{schema_response._id}/actions/'


def configure_test_preconditions(
        registration_status='public',
        reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
        schema_response_state=DEFAULT_SCHEMA_RESPONSE_STATE,
        role='admin'):
    '''Create and Configure a RegistrationProvider, Registration, SchemaResponse, and User.'''
    provider = RegistrationProviderFactory()
    update_provider_auth_groups()
    provider.reviews_workflow = reviews_workflow
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

    schema_response = registration.schema_responses.last()
    schema_response.approvals_state_machine.set_state(schema_response_state)
    schema_response.save()

    auth = configure_auth(registration, role)

    # Do this step after configuring auth to ensure any new admin user gets added
    if schema_response_state is ApprovalStates.UNAPPROVED:
        schema_response_state.pending_approvers.add(
            *registration.get_admin_contributors_recursive()
        )
    return auth, schema_response, registration, provider


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


def make_payload(schema_response, trigger=DEFAULT_TRIGGER):
    return {
        'data':
            {
                'type': 'schema-response-actions',
                'attributes': {
                    'trigger': trigger.db_name,
                    'comment': "It's Party time!",
                },
                'relationships': {
                    'target': {
                        'data': {
                            'id': schema_response._id,
                            'type': 'schema-responses'
                        }
                    }
                }
            }
    }


@pytest.mark.django_db
class TestSchemaResponseActionListGETPermissions:
    '''Checks access for GET requests to the RegistrationSchemaResponseList Endpoint.'''

    def get_status_code_for_preconditions(
            self, registration_status, schema_response_state, reviews_workflow, role):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == 'deleted':
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # FORBIDDEN for authenticated users,
        # UNAUTHORIZED for unauthenticated users
        if registration_status == 'withdrawn':
            if role == 'unauthenticated':
                return 401
            return 403

        # All users can GET APPROVED responses on public registrations
        if registration_status == 'public' and schema_response_state is ApprovalStates.APPROVED:
            return 200

        # unauthenticated users and non-contributors cannot see any other responses
        if role == 'unauthenticated':
            return 401
        if role == 'non-contributor':
            return 403

        # Moderators can GET PENDING_MODERATION and APPROVED SchemaResponses on
        # public or private registrations that are part of a moderated registry
        if role == 'moderator':
            moderator_visible_states = [ApprovalStates.PENDING_MODERATION, ApprovalStates.APPROVED]
            if schema_response_state in moderator_visible_states and reviews_workflow is not None:
                return 200
            else:
                return 403

        # Contributors on the parent registration can GET schema responses in any state,
        # even if the parent_registration is private
        if role in ['read', 'write', 'admin']:
            return 200

        raise ValueError(f'Unrecognized role {role}')

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('role', ['read', 'write', 'admin', 'non-contributor', 'unauthenticated'])
    def test_status_code__as_user(self, app, registration_status, schema_response_state, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role
        )

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('reviews_workflow', [ModerationWorkflows.PRE_MODERATION.value, None])
    def test_status_code__as_moderator(
            self, app, registration_status, schema_response_state, reviews_workflow):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=reviews_workflow,
            role='moderator'
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=reviews_workflow,
            role='moderator'
        )

        resp = app.get(
            make_api_url(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status='deleted', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='deleted',
            schema_response_state=schema_response.state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role
        )

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status='withdrawn', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='withdrawn',
            schema_response_state=schema_response.state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role
        )

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestSchemaResponseActionListGETBehavior:

    def test_get_schema_response_actions(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )

        schema_response.submit(user=auth.user, required_approvers=[auth.user])
        schema_response.approve(user=auth.user)

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        data = resp.json['data']
        assert len(data) == 2
        assert data[0]['attributes']['trigger'] == Triggers.SUBMIT.db_value
        assert data[1]['attributes']['trigger'] == Triggers.APPROVE.db_value


@pytest.mark.django_db
class TestSchemaResponseActionListPOSTPermissions:

    def get_status_code_for_preconditions(self, registration_status, trigger, role):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == 'deleted':
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # FORBIDDEN for authenticated users,
        # UNAUTHORIZED for unauthenticated users
        if registration_status == 'withdrawn':
            if role == 'unauthenticated':
                return 401
            return 403

        # Admin users can SUBMIT, APPROVE, and ADMIN_REJECT SchemaResponses
        # (state conflicts tested elsewhere)
        admin_triggers = [Triggers.SUBMIT, Triggers.APPROVE, Triggers.ADMIN_REJECT]
        if role == 'admin' and trigger in admin_triggers:
            return 201

        # Admin users can ACCEPT and MODERATOR_REJECT SchemaResponses
        # (state conflicts tested elsewhere)
        moderator_triggers = [Triggers.ACCEPT, Triggers.MODERATOR_REJECT]
        if role == 'moderator' and trigger in moderator_triggers:
            return 201

        # All other cases result in:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for all others
        if role == 'unauthenticated':
            return 401
        return 403

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('trigger', Triggers)
    @pytest.mark.parametrize('reviews_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    def test_post_status_code__withdrawn_parent(self, app, reviews_workflow, trigger, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status='withdrawn',
            reviews_workflow=reviews_workflow,
            role=role,
        )
        payload = make_payload(schema_response)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status='withdrawn',
            trigger=trigger,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('trigger', Triggers)
    @pytest.mark.parametrize('reviews_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    def test_post_status_code__deleted_parent(self, app, reviews_workflow, trigger, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status='deleted',
            reviews_workflow=reviews_workflow,
            role=role,
        )
        payload = make_payload(schema_response)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status='deleted',
            trigger=trigger,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('reviews_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    def test_post_status_code__submit(self, app, registration_status, reviews_workflow, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=reviews_workflow,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.SUBMIT,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('reviews_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    def test_post_status_code__approve(self, app, registration_status, reviews_workflow, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=reviews_workflow,
            schema_response_state=ApprovalStates.UNAPPROVED,
            role=role,
        )
        payload = make_payload(schema_response, trigger=Triggers.APPROVE)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.APPROVE,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('reviews_workflow', [None, ModerationWorkflows.PRE_MODERATION.value])
    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    def test_post_status_code__admin_reject(self, app, registration_status, reviews_workflow, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=reviews_workflow,
            schema_response_state=ApprovalStates.UNAPPROVED,
            role=role,
        )
        payload = make_payload(schema_response, trigger=Triggers.ADMIN_REJECT)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.ADMIN_REJECT,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    def test_post_status_code__accept(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=ModerationWorkflows.PRE_MODERATION.value,
            schema_response_state=ApprovalStates.PENDING_MODERATION,
            role=role,
        )
        payload = make_payload(schema_response, trigger=Triggers.ACCEPT)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.ACCEPT,
            role=role
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    def test_post_status_code__moderator_reject(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=ModerationWorkflows.PRE_MODERATION.value,
            schema_response_state=ApprovalStates.PENDING_MODERATION,
            role=role,
        )
        payload = make_payload(schema_response, trigger=Triggers.MODERATOR_REJECT)

        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.MODERATOR_REJECT,
            role=role
        )
        assert resp.status_code == expected_status_code


@pytest.mark.django_db
class TestSchemaResponseActionListPOSTBehavior:
    pass
