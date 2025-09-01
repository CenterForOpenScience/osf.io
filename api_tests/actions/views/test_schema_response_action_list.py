import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows

from osf.models import OSFUser
from osf.utils.workflows import ApprovalStates, SchemaResponseTriggers as Triggers

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)
from osf_tests.utils import get_default_test_schema


USER_ROLES = ['read', 'write', 'admin', 'moderator', 'non-contributor', 'unauthenticated']
UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
DEFAULT_SCHEMA_RESPONSES = {'q1': 'answer', 'q2': 'answer 2', 'q3': 'A', 'q4': ['D']}
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
    provider.update_group_permissions()
    provider.reviews_workflow = reviews_workflow
    provider.save()

    registration = RegistrationFactory(provider=provider, schema=get_default_test_schema())
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
    # Set the required fields on the schema response
    for block in schema_response.response_blocks.all():
        block.set_response(DEFAULT_SCHEMA_RESPONSES.get(block.schema_key))

    auth = configure_user_auth(registration, role)

    # Do this step after configuring auth to ensure any new admin user, gets added
    if schema_response_state is ApprovalStates.UNAPPROVED:
        schema_response.pending_approvers.add(
            *[user for user, _ in registration.get_admin_contributors_recursive()]
        )

    if schema_response_state is ApprovalStates.IN_PROGRESS:
        # need valid changes for submission validations
        schema_response.update_responses({'q1': 'update for submission'})
        schema_response.revision_justification = 'has for valid revision_justification for submission'
        schema_response.save()

    return auth, schema_response, registration, provider


def configure_user_auth(registration, role):
    '''Create a user, and assign appropriate permissions for the given role.'''
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


def get_user_for_auth(auth):
    return OSFUser.objects.get(username=auth[0])

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
    def test_GET_status_code__as_user(self, app, registration_status, schema_response_state, role):
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
    def test_GET_status_code__as_moderator(
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

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_GET_status_code__deleted_parent(self, app, role):
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
    def test_GET_status_code__withdrawn_parent(self, app, role):
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
class TestSchemaResponseActionListGETBehavior:

    def test_GET_schema_response_actions(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )

        user = get_user_for_auth(auth)
        schema_response.submit(user=user, required_approvers=[user])
        schema_response.approve(user=user)

        resp = app.get(make_api_url(schema_response), auth=auth, expect_errors=True)
        data = resp.json['data']
        assert len(data) == 2
        assert data[0]['attributes']['trigger'] == Triggers.SUBMIT.db_name
        assert data[1]['attributes']['trigger'] == Triggers.APPROVE.db_name


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
    @pytest.mark.parametrize('registration_status', ['public', 'private', 'deleted', 'withdrawn'])
    def test_POST_status_code__submit(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.SUBMIT,
            role=role
        )

        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private', 'deleted', 'withdrawn'])
    def test_POST_status_code__approve(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.UNAPPROVED,
            role=role,
        )
        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.APPROVE,
            role=role
        )

        payload = make_payload(schema_response, trigger=Triggers.APPROVE)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private', 'deleted', 'withdrawn'])
    def test_POST_status_code__admin_reject(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.UNAPPROVED,
            role=role,
        )
        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.ADMIN_REJECT,
            role=role
        )

        payload = make_payload(schema_response, trigger=Triggers.ADMIN_REJECT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private', 'deleted', 'withdrawn'])
    def test_POST_status_code__accept(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=ModerationWorkflows.PRE_MODERATION.value,
            schema_response_state=ApprovalStates.PENDING_MODERATION,
            role=role,
        )
        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.ACCEPT,
            role=role
        )

        payload = make_payload(schema_response, trigger=Triggers.ACCEPT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('role', USER_ROLES)
    @pytest.mark.parametrize('registration_status', ['public', 'private', 'deleted', 'withdrawn'])
    def test_POST_status_code__moderator_reject(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_test_preconditions(
            registration_status=registration_status,
            reviews_workflow=ModerationWorkflows.PRE_MODERATION.value,
            schema_response_state=ApprovalStates.PENDING_MODERATION,
            role=role,
        )
        expected_status_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            trigger=Triggers.MODERATOR_REJECT,
            role=role
        )

        payload = make_payload(schema_response, trigger=Triggers.MODERATOR_REJECT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        assert resp.status_code == expected_status_code


@pytest.mark.django_db
class TestSchemaResponseActionListPOSTBehavior:

    def test_POST_submit__denies_unchanged_submission(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )
        schema_response.updated_response_blocks.all().delete()
        assert schema_response.updated_response_keys == set()
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )
        assert resp.status_code == 400
        assert resp.json['errors'][0]['detail'] == 'Cannot submit SchemaResponses without a revision justification or updated registration responses.'

    def test_POST_submit__denies_submission_without_justification(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )
        schema_response.revision_justification = ''
        schema_response.save()

        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )
        assert resp.status_code == 400
        assert resp.json['errors'][0]['detail'] == 'Cannot submit SchemaResponses without a revision justification or updated registration responses.'

    def test_POST_submit__writes_action_and_advances_state(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )
        assert not schema_response.actions.exists()

        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.SUBMIT.db_name
        assert action.creator == get_user_for_auth(auth)
        assert action.from_state == ApprovalStates.IN_PROGRESS.db_name
        assert action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert schema_response.state is ApprovalStates.UNAPPROVED

    def test_POST_submit__assigns_pending_approvers(self, app):
        auth, schema_response, registration, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS, role='admin'
        )
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        pending_approver_ids = set(schema_response.pending_approvers.values_list('id', flat=True))
        assert pending_approver_ids == {get_user_for_auth(auth).id, registration.creator.id}

    @pytest.mark.parametrize(
        'schema_response_state',
        [state for state in ApprovalStates if state is not ApprovalStates.IN_PROGRESS]
    )
    def test_POST_submit__fails_with_invalid_schema_response_state(
            self, app, schema_response_state):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=schema_response_state, role='admin'
        )

        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        assert resp.status_code == 409

    @pytest.mark.parametrize(
        'reviews_workflow, end_state',
        [
            (ModerationWorkflows.PRE_MODERATION.value, ApprovalStates.PENDING_MODERATION),
            (None, ApprovalStates.APPROVED)
        ]
    )
    def test_POST_approve__writes_action_and_advances_state(self, app, reviews_workflow, end_state):
        auth, schema_response, registration, _ = configure_test_preconditions(
            reviews_workflow=reviews_workflow,
            schema_response_state=ApprovalStates.UNAPPROVED,
            role='admin'
        )
        assert not schema_response.actions.exists()

        payload = make_payload(schema_response, trigger=Triggers.APPROVE)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.APPROVE.db_name
        assert action.creator == get_user_for_auth(auth)
        assert action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert schema_response.state is ApprovalStates.UNAPPROVED

        app.post_json_api(make_api_url(schema_response), payload, auth=registration.creator.auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.APPROVE.db_name
        assert action.creator == registration.creator
        assert action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert action.to_state == end_state.db_name
        assert schema_response.state is end_state

    @pytest.mark.parametrize(
        'schema_response_state',
        [state for state in ApprovalStates if state is not ApprovalStates.UNAPPROVED]
    )
    def test_POST_approve__fails_with_invalid_schema_response_state(
            self, app, schema_response_state):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=schema_response_state, role='admin'
        )

        payload = make_payload(schema_response, trigger=Triggers.APPROVE)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        assert resp.status_code == 409

    def test_POST_admin_reject__writes_action_and_advances_state(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.UNAPPROVED, role='admin'
        )
        assert not schema_response.actions.exists()

        payload = make_payload(schema_response, trigger=Triggers.ADMIN_REJECT)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.ADMIN_REJECT.db_name
        assert action.creator == get_user_for_auth(auth)
        assert action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert schema_response.state is ApprovalStates.IN_PROGRESS

    @pytest.mark.parametrize(
        'schema_response_state',
        [state for state in ApprovalStates if state is not ApprovalStates.UNAPPROVED]
    )
    def test_POST_admin_reject__fails_with_invalid_schema_response_state(
            self, app, schema_response_state):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=schema_response_state, role='admin'
        )

        payload = make_payload(schema_response, trigger=Triggers.ADMIN_REJECT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        # handle the weirdness of MODERATOR_REJECT and ADMIN_REJECT getting squashed down
        # to a single trigger on the model
        expected_code = 403 if schema_response_state is ApprovalStates.PENDING_MODERATION else 409
        assert resp.status_code == expected_code

    def test_POST_accept__writes_action_and_advances_state(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.PENDING_MODERATION, role='moderator'
        )
        assert not schema_response.actions.exists()

        payload = make_payload(schema_response, trigger=Triggers.ACCEPT)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.ACCEPT.db_name
        assert action.creator == get_user_for_auth(auth)
        assert action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert action.to_state == ApprovalStates.APPROVED.db_name
        assert schema_response.state is ApprovalStates.APPROVED

    @pytest.mark.parametrize(
        'schema_response_state',
        [state for state in ApprovalStates if state is not ApprovalStates.PENDING_MODERATION]
    )
    def test_POST_accept__fails_with_invalid_schema_response_state(
            self, app, schema_response_state):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=schema_response_state, role='moderator'
        )

        payload = make_payload(schema_response, trigger=Triggers.ACCEPT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        assert resp.status_code == 409

    def test_POST_moderator_reject__writes_action_and_advances_state(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.PENDING_MODERATION, role='moderator'
        )
        assert not schema_response.actions.exists()

        payload = make_payload(schema_response, trigger=Triggers.MODERATOR_REJECT)
        app.post_json_api(make_api_url(schema_response), payload, auth=auth)

        schema_response.refresh_from_db()
        action = schema_response.actions.last()
        assert action.trigger == Triggers.MODERATOR_REJECT.db_name
        assert action.creator == get_user_for_auth(auth)
        assert action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert schema_response.state is ApprovalStates.IN_PROGRESS

    @pytest.mark.parametrize(
        'schema_response_state',
        [state for state in ApprovalStates if state is not ApprovalStates.PENDING_MODERATION]
    )
    def test_POST_moderator_reject__fails_with_invalid_schema_response_state(
            self, app, schema_response_state):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=schema_response_state, role='moderator'
        )

        payload = make_payload(schema_response, trigger=Triggers.MODERATOR_REJECT)
        resp = app.post_json_api(
            make_api_url(schema_response), payload, auth=auth, expect_errors=True
        )

        # handle the weirdness of MODERATOR_REJECT and ADMIN_REJECT getting squashed down
        # to a single trigger on the model
        expected_code = 403 if schema_response_state is ApprovalStates.UNAPPROVED else 409
        assert resp.status_code == expected_code

    def test_POST__no_comment(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS
        )
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        del payload['data']['attributes']['comment']

        resp = app.post_json_api(make_api_url(schema_response), payload, auth=auth)
        assert resp.json['data']['attributes']['comment'] == ''
        assert schema_response.actions.first().comment == ''

    def test_POST__empty_comment(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS
        )
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        payload['data']['attributes']['comment'] = ''

        resp = app.post_json_api(make_api_url(schema_response), payload, auth=auth)
        assert resp.json['data']['attributes']['comment'] == ''
        assert schema_response.actions.first().comment == ''

    def test_POST__null_comment(self, app):
        auth, schema_response, _, _ = configure_test_preconditions(
            schema_response_state=ApprovalStates.IN_PROGRESS
        )
        payload = make_payload(schema_response, trigger=Triggers.SUBMIT)
        payload['data']['attributes']['comment'] = None

        resp = app.post_json_api(make_api_url(schema_response), payload, auth=auth)
        assert resp.json['data']['attributes']['comment'] == ''
        assert schema_response.actions.first().comment == ''


@pytest.mark.django_db
class TestSchemaResponseActionListUnsupportedMethods:

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PATCH(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.patch_json_api(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_PUT(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.put_json_api(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_DELETE(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.delete_json_api(make_api_url(schema_response), auth=auth, expect_errors=True)
        assert resp.status_code == 405
