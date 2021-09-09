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
def schema_response(public_registration):
    response = SchemaResponse.create_initial_response(
        parent=public_registration,
        initiator=public_registration.creator,
    )
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    response.update_responses(INITIAL_SCHEMA_RESPONSES)
    return response


@pytest.mark.django_db
class TestSchemaResponseDetailGET:

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    def test_get_public_response_response_code_with_auth(
            app, registration, schema_response, perms_user, role):
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 200

    def test_get_public_response_response_code_no_auth(app, schema_response):
        resp = app.get(
            url_for_schema_response(schema_response),
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        'role, expected_response',
        [(None, 403), ('read', 200), ('write', 200), ('admin', 200)]
    )
    @pytest.mark.parametrize('response_state', NONAPPROVED_RESPONSE_STATES)
    def test_get_unapproved_response_response_code_with_auth(
            app, registration, schema_response, perms_user, role, expected_response, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_response

    @pytest.mark.parametrize('response_state', NONAPPROVED_RESPONSE_STATES)
    def test_get_unapproved_response_response_code_no_auth(app, schema_response, response_state):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        'role, expected_response',
        [(None, 403), ('read', 200), ('write', 200), ('admin', 200)]
    )
    def test_get_private_response_response_code_with_auth(
            app, registration, schema_response, perms_user, role, expected_response):
        registration.is_public = False
        registration.save()
        if role:
            registration.add_contributor(perms_user, role)
        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_response

    def test_get_private_response_response_code_no_auth(app, registration, schema_response):
        registration.is_public = False
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    def test_get_withdrawn_response_response_code_with_auth(
            app, registration, schema_response, perms_user, role):
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 404

    def test_get_withdrawn_response_response_code_no_auth(app, registration, schema_response):
        registration.moderation_state = RegistrationModerationStates.WITHDRAWN.db_name
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 404

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    def test_get_deleted_response_response_code_with_auth(
            app, registration, schema_response, perms_user, role):
        registration.deleted = timezone.now()
        registration.save()
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=perms_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 404

    def test_get_deleted_response_response_code_no_auth(app, registration, schema_response):
        registration.deleted = timezone.now()
        registration.save()

        resp = app.get(
            url_for_schema_response(schema_response),
            auth=None,
            expect_errors=True,
        )
        assert resp.status_code == 404

    def test_schema_response_detail(self, app, schema_response):
        resp = app.get(url_for_schema_response(schema_response))
        data = resp.json['data']

        assert data['id'] == schema_response._id
        assert data['attributes']['revision_justification'] == schema_response.revision_justification
        assert data['attributes']['revision_responses'] == INITIAL_SCHEMA_RESPONSES

    def test_schema_response_pending_current_user_approval(
            self, app, schema_response, admin_user, perms_user):
        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['is_pending_current_user_approval'] is False

        schema_response.pending_approvers.add(admin_user)

        resp = app.get(url_for_schema_response(schema_response), auth=admin_user.auth)
        assert resp.json['data']['is_pending_current_user_approval'] is True

        resp = app.get(url_for_schema_response(schema_response), auth=perms_user.auth)
        assert resp.json['data']['is_pending_current_user_approval'] is False

class TestSchemaResponseDetailPATCH:

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

    @pytest.mark.parametrize(
        'role, expected_response', [(None, 403), ('read', 403), ('write', 200), ('admin', 200)]
    )
    def test_public_response_patch_resposne_code_with_auth(
            self, app, registration, in_progress_schema_response, payload, perms_user, role, expected_response):
        if role:
            registration.add_contributor(perms_user, role)

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == expected_response

    @pytest.mark.parametrize('role', [None, 'read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', UNPATCHABLE_RESPONSE_STATES)
    def test_unsupported_state_patch_response_code_with_auth(
            self, app, registration, in_progress_schema_response, payload, perms_user, role, response_state):
        if role:
            registration.add_contributor(perms_user, role)
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()

        resp = app.patch_json_api(
            url_for_schema_response(in_progress_schema_response),
            payload,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 400

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
        in_progress_schema_response.update_resposnes({'q1': 'update_value'})
        assert in_progress_schema_response.update_response_keys == {'q1'}

        payload['data']['attributes']['revision_responses']['q1'] == INITIAL_SCHEMA_RESPONSES['q1']
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
        assert errors[0]['detail'] == 'Encountered unexpected keys: oops'


class TestSchemaResponseDetailDELETE:

    def test_schema_response_detail_delete(self, app, schema_response, user, url):
        schema_response.parent.add_contributor(user, 'admin')
        resp = app.delete_json_api(url, auth=user.auth)
        assert resp.status_code == 204

        with pytest.raises(SchemaResponse.DoesNotExist):  # shows it was really deleted
            schema_response.refresh_from_db()

class TestSchemaResponseListUnsupportedMethods:

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
        if permission:
            schema_response.parent.add_contributor(user, permission)
        resp = app.delete_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response
