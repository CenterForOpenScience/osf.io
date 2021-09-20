import pytest

from django.utils import timezone

from api.providers.workflows import Workflows

from osf.migrations import update_provider_auth_groups
from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)

USER_ROLES = ['unauthenticated', 'non-contributor', 'read', 'write', 'admin', 'moderator']

INITIAL_SCHEMA_RESPONSES = {
    'q1': 'Some answer',
    'q2': 'Some even longer answer',
    'q3': 'A',
    'q4': ['D', 'G'],
    'q5': None,
    'q6': None
}


@pytest.fixture()
def admin_user():
    return AuthUserFactory()


@pytest.fixture()
def registration(admin_user):
    return RegistrationFactory(creator=admin_user, is_public=True)


@pytest.fixture()
def schema_response(registration):
    response = registration.schema_responses.last()
    response.update_responses(INITIAL_SCHEMA_RESPONSES)
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    return response


def url_for_schema_response(schema_response):
    return f'/v2/schema_responses/{schema_response._id}/'


def configure_permissions_test_preconditions(
        registration_status='public',
        schema_response_state=ApprovalStates.APPROVED,
        moderator_workflow=Workflows.PRE_MODERATION.value,
        role='admin'):
    '''Create and configure a Registration, RegistrationProvider and SchemaResponse.'''
    provider = RegistrationProviderFactory()
    update_provider_auth_groups()
    provider.reviews_workflow = moderator_workflow
    provider.save()

    registration = RegistrationFactory(provider=provider)
    registration.provider = provider
    if registration_status == 'public':
        registration.is_public = True
    elif registration_status == 'private':
        registration.is_public = False
    elif registration_status == 'withdrawn':
        registration.moderation_state = 'withdrawn'
    elif registration_status == 'deleted':
        registration.deleted = timezone.now()
    registration.save()

    schema_response = registration.schema_responses.last()
    schema_response.approvals_state_machine.set_state(schema_response_state)
    schema_response.save()

    auth = _configure_permissions_test_auth(registration, provider, role)
    return registration, schema_response, provider, auth


def _configure_permissions_test_auth(registration, provider, role):
    '''Create a user and assign appropriate permissions for the given role.'''
    if role == 'unauthenticated':
        return None

    user = AuthUserFactory()
    if role == 'moderator':
        provider.get_group('moderator').user_set.add(user)
    elif role == 'non-contributor':
        pass
    else:
        registration.add_contributor(user, role)

    return user.auth


@pytest.mark.django_db
class TestSchemaResponseDetailGETPermissions:
    '''Checks access for GET requests to the SchemaResponseDetail Endpoint'''

    def get_status_code_for_preconditions(
            self, registration_status, schema_response_state, moderator_workflow, role):
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
            if schema_response_state in moderator_visible_states and moderator_workflow is not None:
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
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            role=role
        )
        expected_code = self.get_status_code_for_preconditions_and_role(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('moderator_workflow', [Workflows.PRE_MODERATION.value, None])
    def test_status_code__as_moderator(
            self, app, registration_status, schema_response_state, moderator_workflow):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='deleted', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='deleted',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='withdrawn', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='withdrawn',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailGETBehavior:
    '''Confirms behavior of GET requests agaisnt the SchemaResponseList Endpoint.

    GET should return a serialized instance of the SchemaResponse with the requested ID
    as it exists in the database at the time of the call.

    Additionally, the serialized version should include an 'is_pending_current_user_approval'
    field that is True if the current user is in the SchemaResponse's `pending_approvers` and
    False otherwise.
    '''

    def test_schema_response_detail(self, app, schema_response):
        resp = app.get(url_for_schema_response(schema_response))
        data = resp.json['data']

        assert data['id'] == schema_response._id
        assert data['attributes']['revision_justification'] == schema_response.revision_justification
        assert data['attributes']['revision_responses'] == INITIAL_SCHEMA_RESPONSES
        assert data['attributes']['reviews_state'] == schema_response.reviews_state
        assert data['relationships']['registration']['data']['id'] == schema_response.parent._id
        assert data['relationships']['registration_schema']['data']['id'] == schema_response.schema._id
        assert data['relationships']['initiated_by']['data']['id'] == schema_response.initiator._id

    def test_schema_response_displays_updated_responses(self, app, schema_response, admin_user):
        revised_response = SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=admin_user
        )

        resp = app.get(url_for_schema_response(revised_response), auth=admin_user.auth)
        attributes = resp.json['data']['attributes']
        assert attributes['revision_responses'] == INITIAL_SCHEMA_RESPONSES
        assert not attributes['updated_response_keys']

        revised_response.update_responses({'q1': 'updated response'})

        expected_responses = dict(INITIAL_SCHEMA_RESPONSES, q1='updated response')
        resp = app.get(url_for_schema_response(revised_response), auth=admin_user.auth)
        attributes = resp.json['data']['attributes']
        assert attributes['revision_responses'] == expected_responses
        assert attributes['updated_response_keys'] == ['q1']

    def test_schema_response_pending_current_user_approval(self, app, schema_response, admin_user):
        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is False

        schema_response.pending_approvers.add(admin_user)

        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is True

        alternate_user = AuthUserFactory()
        resp = app.get(url_for_schema_response(schema_response), auth=alternate_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is False


@pytest.mark.django_db
class TestSchemaResponseDetailPATCHPermissions:
    '''Checks the status codes for PATCHing to SchemaResponseDetail under various conditions.'''

    PAYLOAD = {
        'data': {
            'type': 'revisions',
            'attributes': {
                'revision_responses': {
                    'q1': 'update value',
                    'q2': INITIAL_SCHEMA_RESPONSES['q2'],  # fake it out by adding an old value
                }
            }
        }
    }

    def get_status_code_for_preconditions(
            self, registration_status, schema_response_state, moderator_workflow, role):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == 'deleted':
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for all others
        if registration_status == 'withdrawn':
            if role == 'unauthenticated':
                return 401
            return 403

        # PATCH succeeds for write and admin contributors on the parent registratoin
        # so long as the schema_response is IN_PROGRESS.
        # All other states return CONFLICT
        if role in ['write', 'admin']:
            if schema_response_state is ApprovalStates.IN_PROGRESS:
                return 200
            return 409

        # In all other cases, return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for logged-in users
        if role == 'unauthenticated':
            return 401
        return 403

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('role', ['read', 'write', 'admin', 'non-contributor', 'unauthenticated'])
    def test_status_code__as_user(self, app, registration_status, schema_response_state, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.patch_json_api(
            url_for_schema_response(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('moderator_workflow', [Workflows.PRE_MODERATION.value, None])
    def test_status_code__as_moderator(
            self, app, registration_status, schema_response_state, moderator_workflow):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )

        resp = app.patch_json_api(
            url_for_schema_response(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='deleted', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='deleted',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.patch_json_api(
            url_for_schema_response(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='withdrawn', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='withdrawn',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.patch_json_api(
            url_for_schema_response(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailPATCHBehavior:

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'type': 'revisions',
                'attributes': {
                    'revision_justification': 'why not?',
                    'revision_responses': {
                        'q1': 'update value',
                        'q2': INITIAL_SCHEMA_RESPONSES['q2'],  # fake it out by adding an old value
                    }
                }
            }
        }

    @pytest.fixture()
    def invalid_payload(self):
        return {
            'data': {
                'type': 'revisions',
                'attributes': {
                    'revision_responses': {
                        'oops': {'value': 'test'},
                        'q2': {'value': 'test2'},
                    }
                }
            }
        }

    @pytest.fixture()
    def in_progress_schema_response(self, schema_response):
        return SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=schema_response.initiator
        )

    def test_patch_sets_responses(self, app, in_progress_schema_response, payload, admin_user):
        assert in_progress_schema_response.all_responses == INITIAL_SCHEMA_RESPONSES

        app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=admin_user.auth
        )

        expected_responses = dict(INITIAL_SCHEMA_RESPONSES, q1='update value')
        in_progress_schema_response.refresh_from_db()
        assert in_progress_schema_response.all_responses == expected_responses

    def test_patch_sets_updated_response_keys(
            self, app, in_progress_schema_response, payload, admin_user):
        assert not in_progress_schema_response.updated_response_keys

        app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=admin_user.auth
        )

        in_progress_schema_response.refresh_from_db()
        assert in_progress_schema_response.updated_response_keys == {'q1'}

    def test_patch_with_old_answer_removes_updated_response_keys(
            self, app, in_progress_schema_response, payload, admin_user):
        in_progress_schema_response.update_responses({'q1': 'update_value'})
        assert in_progress_schema_response.updated_response_keys == {'q1'}

        payload['data']['attributes']['revision_responses']['q1'] = INITIAL_SCHEMA_RESPONSES['q1']
        app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=admin_user.auth
        )

        in_progress_schema_response.refresh_from_db()
        assert not in_progress_schema_response.updated_response_keys

    def test_patch_fails_with_invalid_keys(
            self, app, in_progress_schema_response, invalid_payload, admin_user):
        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            invalid_payload,
            auth=admin_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 400

        errors = resp.json['errors']
        assert len(errors) == 1
        # Check for the invalid key in the error message
        assert 'oops' in errors[0]['detail']

    def test_patch_updates_revision_response(
            self, app, in_progress_schema_response, payload, admin_user):
        app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=admin_user.auth
        )

        in_progress_schema_response.refresh_from_db()
        assert in_progress_schema_response.revision_justification == 'why not?'


@pytest.mark.django_db
class TestSchemaResponseDetailDELETEPermissions:
    '''Checks the status codes for PATCHing to SchemaResponseDetail under various conditions.

    Only users with ADMIN permissions on the parent resource should be able to
    DELETE a SchemaResponse, so long as the SchemaResponse is IN_PROGRESS, even if the
    parent resource is not public.

    DELETEing a SchemaResponse with a parent resource that has been deleted or withdrawn
    should result in a 410 or 403, respectively.
    '''

    def get_status_code_for_preconditions_and_role(
            self, registration_status, schema_response_state, moderator_workflow, role):
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

        # Admin users on the parent registration can delete schema_responses in state IN_PROGRESS
        # All other schema_response_states return CONFLICT
        if role == 'admin':
            if schema_response_state is ApprovalStates.IN_PROGRESS:
                return 204
            return 409

        # In all other cases, return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for logged-in users
        if role == 'unauthenticated':
            return 401
        return 403

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('role', ['read', 'write', 'admin', 'non-contributor', 'unauthenticated'])
    def test_status_code__as_user(self, app, registration_status, schema_response_state, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('registration_status', ['public', 'private'])
    @pytest.mark.parametrize('schema_response_state', ApprovalStates)
    @pytest.mark.parametrize('moderator_workflow', [Workflows.PRE_MODERATION.value, None])
    def test_status_code__as_moderator(
            self, app, registration_status, schema_response_state, moderator_workflow):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            moderator_workflow=moderator_workflow,
            role='moderator'
        )

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='deleted', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='deleted',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            registration_status='withdrawn', role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status='withdrawn',
            schema_response_state=schema_response.state,
            moderator_workflow=provider.reviews_workflow,
            role=role
        )

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailDELETEBehavior:
    '''Tests behavior of DELETE requests to the SchemaResponseDetail endpoint.

    DELETE requests should delete the specified SchemaResponse from the database.
    '''

    @pytest.fixture()
    def in_progress_schema_response(self, schema_response):
        return SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=schema_response.initiator
        )

    def test_schema_response_detail_delete(self, app, in_progress_schema_response, admin_user):
        app.delete_json_api(
            url_for_schema_response(in_progress_schema_response),
            auth=admin_user.auth
        )

        with pytest.raises(SchemaResponse.DoesNotExist):  # shows it was really deleted
            in_progress_schema_response.refresh_from_db()


@pytest.mark.django_db
class TestSchemaResponseListUnsupportedMethods:
    '''Confirm that the SchemaResponseDetail endpoint does not support POST or PUT'''

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_post(self, app, role):
        # Most permissive preconditions
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            role=role
        )

        resp = app.post_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', USER_ROLES)
    def test_cannot_put(self, app, role):
        # Most permissive preconditions
        registration, schema_response, provider, auth = configure_permissions_test_preconditions(
            role=role
        )

        resp = app.put_json_api(
            url_for_schema_response(schema_response),
            auth=auth,
            expect_errors=True
        )
        assert resp.status_code == 405
