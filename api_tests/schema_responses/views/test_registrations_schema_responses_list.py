import pytest

from django.utils import timezone

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from osf_tests.factories import (
    # SchemaResponseFactory,
    RegistrationFactory,
    AuthUserFactory,
)

UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]

@pytest.fixture()
def admin_user():
    return AuthUserFactory()


@pytest.fixture()
def perms_user():
    return AuthUserFactory()


@pytest.fixture()
def registration(admin_user):
    return RegistrationFactory(creator=admin_user)


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

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_public_registration_responses_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.is_public = True
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )

        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_public_registration_responses_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        registration.is_public = True
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == 200

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_private_registration_responses_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )

        assert resp.status_code == 200

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_private_registration_responses_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        registration.is_public = False
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_withdrawn_registration_responses_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.moderation_state = 'withdrawn'
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )

        assert resp.status_code == 403

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_withdrawn_registration_responses_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        registration.moderation_state = 'withdrawn'
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == (403 if use_auth else 401)

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_get_deleted_registration_responses_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        registration.deleted = timezone.now()
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )

        assert resp.status_code == 410

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_get_deleted_registration_responses_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        registration.deleted = timezone.now()
        registration.save()
        resp = app.get(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )

        assert resp.status_code == 410


@pytest.mark.django_db
class TestRegistrationSchemaResponseListGETBehavior:
    '''Test the results from GET requests against the RegistrationSchemaResponse endpoint.

    Contributors on the base Registration should be able to see all SchemaResponses
    on a registration, whether approved or not, whether the Registration is public
    or private.

    Non-contributors should only see APPROVED SchemaResponses on Public registrations
    (permissions tests verify 403/401 response for non-contributors on a private registration).
    '''

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_get_schema_responses_on_public_registration_as_contributor(
            self, app, url, registration, approved_response, non_approved_response, perms_user, role, response_state):
        registration.add_contributor(perms_user, role)
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        expected_ids = {approved_response._id, non_approved_response._id}
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('use_auth', [True, False])
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_get_schema_responses_on_public_registration_as_non_contributor(
            self, app, url, registration, approved_response, non_approved_response, perms_user, use_auth, response_state):
        registration.is_public = True
        registration.save()
        resp = app.get(url, auth=perms_user.auth if use_auth else None)

        expected_ids = {approved_response._id}
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    @pytest.mark.parametrize('response_state', UNAPPROVED_RESPONSE_STATES)
    def test_get_schema_responses_on_private_registration_as_contributor(
            self, app, url, registration, approved_response, non_approved_response, perms_user, role, response_state):
        registration.add_contributor(perms_user, role)
        registration.is_public = False
        registration.save()
        resp = app.get(url, auth=perms_user.auth)

        expected_ids = {approved_response._id, non_approved_response._id}
        encountered_ids = set(entry['id'] for entry in resp.json['data'])
        assert encountered_ids == expected_ids


@pytest.mark.django_db
class TestRegistrationSchemaResponseListUnsupportedMethods:
    '''Make sure that RegistrationSchemaResponseList does not support POST, PUT, PATCH or DELETE.'''

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_post_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        resp = app.post_json_api(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_post_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        resp = app.post_json_api(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_patch_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        resp = app.patch_json_api(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_patch_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        resp = app.patch_json_api(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_put_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        resp = app.put_json_api(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_put_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        resp = app.put_json_api(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('role', ['read', 'write', 'admin'])
    def test_delete_as_contributor(
            self, app, url, registration, perms_user, role):
        registration.add_contributor(perms_user, role)
        resp = app.delete_json_api(
            url,
            auth=perms_user.auth,
            expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize('use_auth', [True, False])
    def test_delete_as_non_contributor(
            self, app, url, registration, perms_user, use_auth):
        resp = app.delete_json_api(
            url,
            auth=perms_user.auth if use_auth else None,
            expect_errors=True
        )
        assert resp.status_code == 405
