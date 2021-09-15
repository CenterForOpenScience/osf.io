import pytest

from django.utils import timezone

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
)

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates


NONAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
UNPATCHABLE_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.IN_PROGRESS
]

INITIAL_SCHEMA_RESPONSES = {
    'q1': 'Some answer',
    'q2': 'Some even longer answer',
    'q3': 'A',
    'q4': ['D', 'G'],
    'q5': None,
    'q6': None
}


def url_for_schema_response(schema_response):
    return f'/v2/schema_responses/{schema_response._id}/'


@pytest.fixture()
def admin_user():
    return AuthUserFactory()


@pytest.fixture()
def perms_user():
    return AuthUserFactory()


@pytest.fixture()
def registration(admin_user):
    return RegistrationFactory(creator=admin_user, is_public=True)


@pytest.fixture()
def schema_response(registration):
    response = SchemaResponse.create_initial_response(
        parent=registration,
        initiator=registration.creator,
    )
    response.update_responses(INITIAL_SCHEMA_RESPONSES)
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    return response


@pytest.mark.django_db
class TestSchemaResponseDetailGETPermissions:
    '''Checks the status codes for GET requests to the SchemaResponseDetail Endpoint

    All users should be able to GET SchemaResponses that are APPROVED and on a public registration.
    SchemaResponses with a private parent registration and those in states other than APPROVED
    should only be visible to contributors on the registration -- unless the user is a moderator
    on the parent registration's provider and the SchemaResponse is PENDING_MODERATION.

    GETing a SchemaResponses whose parent registration has been deleted or withdrawn should result
    in a 410 or 403, respectively
    '''

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_public_response_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_public_response_status_code_as_non_contributor(
            self, app, schema_response, perms_user, use_auth):
        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True,
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', NONAPPROVED_RESPONSE_STATES)
    def test_get_unapproved_response_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role, response_state):
        registration.add_contributor(perms_user, role)
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    @pytest.mark.parametrize('response_state', NONAPPROVED_RESPONSE_STATES)
    def test_get_unapproved_response_status_code_as_non_contributor(
            self, app, schema_response, response_state, perms_user, use_auth):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True,
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_response__of_private_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()
        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_response_of_private_registration_status_code_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.is_public = False
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True,
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_response_of_withdrawn_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_response_of_withdrawn_registration_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True,
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_response_of_deleted_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.deleted = timezone.now()
        registration.save()
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_response_of_deleted_registration_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.deleted = timezone.now()
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True,
        )
        assert resp.status_code == 410


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

    def test_schema_response_pending_current_user_approval(
            self, app, schema_response, admin_user, perms_user):
        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is False

        schema_response.pending_approvers.add(admin_user)

        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is True

        resp = app.get(url_for_schema_response(schema_response), auth=perms_user.auth)
        assert resp.json['data']['attributes']['is_pending_current_user_approval'] is False


@pytest.mark.django_db
class TestSchemaResponseDetailPATCHPermissions:
    '''Checks the status codes for PATCHing to SchemaResponseDetail under various conditions.

    Only 'ADMIN' and 'WRITE' contributors should be able to PATCH to a SchemaResponse.
    'ADMIN' and 'WRITE' contributors can PATCH whether the parent registration is public
    or private, but cannot PATCH a SchemaResponse with a state other than IN_PROGRESS.

    PATCHing to a SchemaResponse whose parent registration has been deleted or withdrawn should
    result in a 410 or a 403, respectively
    '''

    @pytest.fixture()
    def payload(self):
        return {
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

    @pytest.fixture()
    def in_progress_schema_response(self, schema_response):
        return SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=schema_response.initiator
        )

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 200), ('admin', 200)])
    def test_patch_public_response_status_code_as_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, role, expected_code):
        registration.add_contributor(perms_user, role)

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_patch_public_response_status_code_as_non_contributor(
            self, app, in_progress_schema_response, payload, perms_user, use_auth):
        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 200), ('admin', 200)])
    def test_patch_response_of_private_registration_status_code_as_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, role, expected_code):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_patch_response_of_private_registration_status_code_as_non_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, use_auth):
        registration.is_public = False
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 409), ('admin', 409)])
    @pytest.mark.parametrize('response_state', UNPATCHABLE_RESPONSE_STATES)
    def test_patch_response_in_unsupported_state_status_code_as_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, role, response_state, expected_code):
        registration.add_contributor(perms_user, role)
        in_progress_schema_response.approvals_state_machine.set_state(response_state)
        in_progress_schema_response.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    @pytest.mark.parametrize('response_state', UNPATCHABLE_RESPONSE_STATES)
    def test_patch_response_in_unsupported_state_status_code_as_non_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, use_auth, response_state):
        in_progress_schema_response.approvals_state_machine.set_state(response_state)
        in_progress_schema_response.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_patch_response_of_withdrawn_registration_status_code_as_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_patch_response_of_withdrawn_registration_status_code_as_non_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, use_auth):
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_patch_response_of_deleted_registration_status_code_as_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.deleted = timezone.now()
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_patch_response_of_deleted_registration_status_code_as_non_contributor(
            self, app, registration, in_progress_schema_response, payload, perms_user, use_auth):
        registration.deleted = timezone.now()
        registration.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 410


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

    def test_patch_sets_responses(
            self, app, in_progress_schema_response, payload, admin_user):
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

    @pytest.fixture()
    def schema_response(self, registration):
        return SchemaResponse.create_initial_response(
            parent=registration,
            initiator=registration.creator
        )

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 403), ('admin', 204)])
    def test_delete_public_response_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role, expected_code):
        registration.add_contributor(perms_user, role)

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_delete_public_response_status_code_as_non_contributor(
            self, app, schema_response, perms_user, use_auth):
        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 403), ('admin', 204)])
    def test_delete_response_of_private_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role, expected_code):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_delete_response_of_private_registration_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.is_public = False
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role, expected_code', [('read', 403), ('write', 403), ('admin', 409)])
    @pytest.mark.parametrize('response_state', UNPATCHABLE_RESPONSE_STATES)
    def test_delete_response_in_unsupported_state_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role, response_state, expected_code):
        registration.add_contributor(perms_user, role)
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize('use_auth', [True, False])
    @pytest.mark.parametrize('response_state', UNPATCHABLE_RESPONSE_STATES)
    def test_delete_response_in_unsupported_state_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_delete_response_of_withdrawn_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_delete_response_of_withdrawn_registration_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_delete_response_of_deleted_registration_status_code_as_contributor(
            self, app, registration, schema_response, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.deleted = timezone.now()
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_delete_response_of_deleted_registration_status_code_as_non_contributor(
            self, app, registration, schema_response, perms_user, use_auth):
        registration.deleted = timezone.now()
        registration.save()

        resp = app.delete_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 410


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

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_cannot_post_as_contributor(
            self, app, schema_response, perms_user, role):
        schema_response.parent.add_contributor(perms_user, role)
        resp = app.post_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_post_as_non_contributor(
            self, app, schema_response, perms_user, use_auth):
        resp = app.post_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == 405

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_cannot_put_as_contributor(
            self, app, schema_response, perms_user, role):
        schema_response.parent.add_contributor(perms_user, role)
        resp = app.put_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_cannot_put_as_non_contributor(
            self, app, schema_response, perms_user, use_auth):
        resp = app.put_json_api(
            url_for_schema_response(schema_response),
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == 405
