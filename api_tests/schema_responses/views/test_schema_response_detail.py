import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)
from osf_tests.utils import get_default_test_schema

USER_ROLES = [
    "unauthenticated",
    "non-contributor",
    "read",
    "write",
    "admin",
    "moderator",
]

INITIAL_SCHEMA_RESPONSES = {
    "q1": "Some answer",
    "q2": "Some even longer answer",
    "q3": "A",
    "q4": ["D", "G"],
    "q5": "",
    "q6": [],
}

IMMUTABLE_STATES = [
    state
    for state in ApprovalStates
    if state is not ApprovalStates.IN_PROGRESS
]

DEFAULT_REVIEWS_WORKFLOW = ModerationWorkflows.PRE_MODERATION.value


@pytest.fixture()
def admin_user():
    return AuthUserFactory()


@pytest.fixture()
def schema():
    return get_default_test_schema()


@pytest.fixture()
def registration(admin_user, schema):
    return RegistrationFactory(
        creator=admin_user, schema=schema, is_public=True
    )


@pytest.fixture()
def schema_response(registration):
    response = registration.schema_responses.last()
    for block in response.response_blocks.all():
        block.response = INITIAL_SCHEMA_RESPONSES[block.schema_key]
        block.save()
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    return response


def make_api_url(schema_response):
    return f"/v2/schema_responses/{schema_response._id}/"


def configure_permissions_test_preconditions(
    registration_status="public",
    schema_response_state=ApprovalStates.APPROVED,
    reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
    role="admin",
):
    """Create and configure a RegistrationProvider, Registration, SchemaResponse and User."""
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = reviews_workflow
    provider.save()

    registration = RegistrationFactory(
        schema=get_default_test_schema(), provider=provider
    )
    registration.provider = provider
    if registration_status == "public":
        registration.is_public = True
    elif registration_status == "private":
        registration.is_public = False
    elif registration_status == "withdrawn":
        registration.moderation_state = "withdrawn"
    elif registration_status == "deleted":
        registration.deleted = timezone.now()
    registration.save()

    schema_response = registration.schema_responses.last()
    schema_response.approvals_state_machine.set_state(schema_response_state)
    schema_response.save()

    auth = _configure_permissions_test_auth(registration, role)
    return auth, schema_response, registration, provider


def _configure_permissions_test_auth(registration, role):
    """Create a user and assign appropriate permissions for the given role."""
    if role == "unauthenticated":
        return None

    user = AuthUserFactory()
    if role == "moderator":
        registration.provider.get_group("moderator").user_set.add(user)
    elif role == "non-contributor":
        pass
    else:
        registration.add_contributor(user, role)

    return user.auth


@pytest.mark.django_db
class TestSchemaResponseDetailGETPermissions:
    """Checks access for GET requests to the SchemaResponseDetail Endpoint"""

    def get_status_code_for_preconditions(
        self,
        registration_status,
        schema_response_state,
        reviews_workflow,
        role,
    ):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == "deleted":
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # FORBIDDEN for authenticated users,
        # UNAUTHORIZED for unauthenticated users
        if registration_status == "withdrawn":
            if role == "unauthenticated":
                return 401
            return 403

        # All users can GET APPROVED responses on public registrations
        if (
            registration_status == "public"
            and schema_response_state is ApprovalStates.APPROVED
        ):
            return 200

        # unauthenticated users and non-contributors cannot see any other responses
        if role == "unauthenticated":
            return 401
        if role == "non-contributor":
            return 403

        # Moderators can GET PENDING_MODERATION and APPROVED SchemaResponses on
        # public or private registrations that are part of a moderated registry
        if role == "moderator":
            moderator_visible_states = [
                ApprovalStates.PENDING_MODERATION,
                ApprovalStates.APPROVED,
            ]
            if (
                schema_response_state in moderator_visible_states
                and reviews_workflow is not None
            ):
                return 200
            else:
                return 403

        # Contributors on the parent registration can GET schema responses in any state,
        # even if the parent_registration is private
        if role in ["read", "write", "admin"]:
            return 200

        raise ValueError(f"Unrecognized role {role}")

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize("schema_response_state", ApprovalStates)
    @pytest.mark.parametrize(
        "role",
        ["read", "write", "admin", "non-contributor", "unauthenticated"],
    )
    def test_status_code__as_user(
        self, app, registration_status, schema_response_state, role
    ):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.get(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize("schema_response_state", ApprovalStates)
    @pytest.mark.parametrize(
        "reviews_workflow", [ModerationWorkflows.PRE_MODERATION.value, None]
    )
    def test_status_code__as_moderator(
        self, app, registration_status, schema_response_state, reviews_workflow
    ):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            schema_response_state=schema_response_state,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )

        resp = app.get(
            make_api_url(schema_response),
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="deleted", role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="deleted",
            schema_response_state=schema_response.state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.get(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="withdrawn", role=role
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="withdrawn",
            schema_response_state=schema_response.state,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.get(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailGETBehavior:
    """Confirms behavior of GET requests agaisnt the SchemaResponseList Endpoint.

    GET should return a serialized instance of the SchemaResponse with the requested ID
    as it exists in the database at the time of the call.

    Additionally, the serialized version should include an 'is_pending_current_user_approval'
    field that is True if the current user is in the SchemaResponse's `pending_approvers` and
    False otherwise.
    """

    def test_schema_response_detail(self, app, schema_response):
        resp = app.get(make_api_url(schema_response))
        data = resp.json["data"]

        assert data["id"] == schema_response._id
        assert (
            data["attributes"]["revision_justification"]
            == schema_response.revision_justification
        )
        assert (
            data["attributes"]["revision_responses"]
            == INITIAL_SCHEMA_RESPONSES
        )
        assert (
            data["attributes"]["reviews_state"]
            == schema_response.reviews_state
        )
        assert (
            data["relationships"]["registration"]["data"]["id"]
            == schema_response.parent._id
        )
        assert (
            data["relationships"]["registration_schema"]["data"]["id"]
            == schema_response.schema._id
        )
        assert (
            data["relationships"]["initiated_by"]["data"]["id"]
            == schema_response.initiator._id
        )

    def test_schema_response_displays_updated_responses(
        self, app, schema_response, admin_user
    ):
        revised_response = SchemaResponse.create_from_previous_response(
            previous_response=schema_response, initiator=admin_user
        )

        resp = app.get(make_api_url(revised_response), auth=admin_user.auth)
        attributes = resp.json["data"]["attributes"]
        assert attributes["revision_responses"] == INITIAL_SCHEMA_RESPONSES
        assert not attributes["updated_response_keys"]

        revised_response.update_responses({"q1": "updated response"})

        expected_responses = dict(
            INITIAL_SCHEMA_RESPONSES, q1="updated response"
        )
        resp = app.get(make_api_url(revised_response), auth=admin_user.auth)
        attributes = resp.json["data"]["attributes"]
        assert attributes["revision_responses"] == expected_responses
        assert attributes["updated_response_keys"] == ["q1"]

    def test_schema_response_pending_current_user_approval(
        self, app, schema_response, admin_user
    ):
        resp = app.get(make_api_url(schema_response), auth=admin_user.auth)
        assert (
            resp.json["data"]["attributes"]["is_pending_current_user_approval"]
            is False
        )

        schema_response.pending_approvers.add(admin_user)

        resp = app.get(make_api_url(schema_response), auth=admin_user.auth)
        assert (
            resp.json["data"]["attributes"]["is_pending_current_user_approval"]
            is True
        )

        alternate_user = AuthUserFactory()
        resp = app.get(make_api_url(schema_response), auth=alternate_user.auth)
        assert (
            resp.json["data"]["attributes"]["is_pending_current_user_approval"]
            is False
        )

    def test_schema_response_is_original_response(
        self, app, schema_response, admin_user
    ):
        resp = app.get(make_api_url(schema_response), auth=admin_user.auth)
        assert resp.json["data"]["attributes"]["is_original_response"] is True

        revision = SchemaResponse.create_from_previous_response(
            previous_response=schema_response, initiator=admin_user
        )
        resp = app.get(make_api_url(revision), auth=admin_user.auth)
        assert resp.json["data"]["attributes"]["is_original_response"] is False


@pytest.mark.django_db
class TestSchemaResponseDetailPATCHPermissions:
    """Checks access for PATCH request to the SchemaResponseDetail Endpoint."""

    PAYLOAD = {
        "data": {
            "type": "schema-responses",
            "attributes": {
                "revision_responses": {
                    "q1": "update value",
                    "q2": INITIAL_SCHEMA_RESPONSES[
                        "q2"
                    ],  # fake it out by adding an old value
                }
            },
        }
    }

    def get_status_code_for_preconditions(
        self, registration_status, reviews_workflow, role
    ):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == "deleted":
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for all others
        if registration_status == "withdrawn":
            if role == "unauthenticated":
                return 401
            return 403

        # PATCH succeeds for write and admin contributors on the parent registration
        # (state-related failures are tested elsewhere)
        if role in ["write", "admin"]:
            return 200

        # In all other cases, return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for logged-in users
        if role == "unauthenticated":
            return 401
        return 403

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize(
        "role",
        ["read", "write", "admin", "non-contributor", "unauthenticated"],
    )
    def test_status_code__as_user(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.patch_json_api(
            make_api_url(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize(
        "reviews_workflow", [ModerationWorkflows.PRE_MODERATION.value, None]
    )
    def test_status_code__as_moderator(
        self, app, registration_status, reviews_workflow
    ):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )

        resp = app.patch_json_api(
            make_api_url(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="deleted",
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="deleted",
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.patch_json_api(
            make_api_url(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="withdrawn",
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="withdrawn",
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.patch_json_api(
            make_api_url(schema_response),
            self.PAYLOAD,
            auth=auth,
            expect_errors=True,
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailPATCHBehavior:
    """Confirms behavior of PATCH requests to the SchemaResponseDetail Endpoint.

    Successful PATCH requests should update the specified SchemaResponse in the database
    to match the provided "revision_responses" and/or "revision_justification".

    Additionally, changes to "revision_responses" relative to any "previous_response" on
    the SchemaResponse should appear in the list of "updated_response_keys".

    Requests that pass an unsupported key in "revision_responses" should return a 400 error,
    while requests against a SchemaResponse in a state other than IN_PROGRESS shoudl 409.
    """

    @pytest.fixture()
    def payload(self):
        return {
            "data": {
                "type": "schema-responses",
                "attributes": {
                    "revision_justification": "why not?",
                    "revision_responses": {
                        "q1": "update value",
                        "q2": INITIAL_SCHEMA_RESPONSES[
                            "q2"
                        ],  # fake it out by adding an old value
                    },
                },
            }
        }

    @pytest.fixture()
    def invalid_payload(self):
        return {
            "data": {
                "type": "schema-responses",
                "attributes": {
                    "revision_responses": {
                        "oops": {"value": "test"},
                        "q2": {"value": "updated value 2"},
                    }
                },
            }
        }

    @pytest.fixture()
    def schema_response(self, schema_response):
        # Use create_from_previous_response to better test update_response_keys behavior
        return SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=schema_response.initiator,
        )

    def test_PATCH_sets_responses(
        self, app, schema_response, payload, admin_user
    ):
        assert schema_response.all_responses == INITIAL_SCHEMA_RESPONSES

        app.patch_json_api(
            make_api_url(schema_response), payload, auth=admin_user.auth
        )

        expected_responses = dict(INITIAL_SCHEMA_RESPONSES, q1="update value")
        schema_response.refresh_from_db()
        assert schema_response.all_responses == expected_responses

    def test_PATCH_sets_updated_response_keys(
        self, app, schema_response, payload, admin_user
    ):
        assert not schema_response.updated_response_keys

        app.patch_json_api(
            make_api_url(schema_response), payload, auth=admin_user.auth
        )

        schema_response.refresh_from_db()
        assert schema_response.updated_response_keys == {"q1"}

    def test_PATCH_with_old_answer_removes_updated_response_keys(
        self, app, schema_response, payload, admin_user
    ):
        schema_response.update_responses({"q1": "update_value"})
        assert schema_response.updated_response_keys == {"q1"}

        payload["data"]["attributes"]["revision_responses"]["q1"] = (
            INITIAL_SCHEMA_RESPONSES["q1"]
        )
        app.patch_json_api(
            make_api_url(schema_response), payload, auth=admin_user.auth
        )

        schema_response.refresh_from_db()
        assert not schema_response.updated_response_keys

    def test_PATCH_updates_revision_justification(
        self, app, schema_response, payload, admin_user
    ):
        app.patch_json_api(
            make_api_url(schema_response), payload, auth=admin_user.auth
        )

        schema_response.refresh_from_db()
        assert schema_response.revision_justification == "why not?"

    def test_PATCH_empty_revision_justification_passes(
        self, app, schema_response, payload, admin_user
    ):
        payload["data"]["attributes"]["revision_justification"] = ""
        resp = app.patch_json_api(
            make_api_url(schema_response),
            payload,
            auth=admin_user.auth,
            expect_errors=True,
        )

        schema_response.refresh_from_db()
        assert resp.status_code == 200

    @pytest.mark.parametrize("response_state", IMMUTABLE_STATES)
    def test_PATCH_fails_in_unsupported_state(
        self, app, schema_response, payload, admin_user, response_state
    ):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        resp = app.patch_json_api(
            make_api_url(schema_response),
            payload,
            auth=admin_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 409

    def test_PATCH_fails_with_invalid_keys(
        self, app, schema_response, invalid_payload, admin_user
    ):
        resp = app.patch_json_api(
            make_api_url(schema_response),
            invalid_payload,
            auth=admin_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 400

        errors = resp.json["errors"]
        assert len(errors) == 1
        # Check for the invalid key in the error message
        assert "oops" in errors[0]["detail"]

    def test_PATCH_with_invalid_keys_fails_atomically(
        self, app, schema_response, invalid_payload, admin_user
    ):
        before_responses = schema_response.all_responses
        app.patch_json_api(
            make_api_url(schema_response),
            invalid_payload,
            auth=admin_user.auth,
            expect_errors=True,
        )

        schema_response.refresh_from_db()
        assert schema_response.all_responses == before_responses


@pytest.mark.django_db
class TestSchemaResponseDetailDELETEPermissions:
    """Checks access for DELETE requests to the SchemaResponseDetail Endpoint."""

    def get_status_code_for_preconditions(
        self, registration_status, reviews_workflow, role
    ):
        # All requests for SchemaResponses on a deleted parent Registration return GONE
        if registration_status == "deleted":
            return 410

        # All requests for SchemaResponses on a withdrawn parent registration return:
        # FORBIDDEN for authenticated users,
        # UNAUTHORIZED for unauthenticated users
        if registration_status == "withdrawn":
            if role == "unauthenticated":
                return 401
            return 403

        # Admin users on the parent registration can DELETE SchemaResponses
        # (state-related failures are tested elsewhere)
        if role == "admin":
            return 204

        # In all other cases, return:
        # UNAUTHORIZED for unauthenticated users
        # FORBIDDEN for logged-in users
        if role == "unauthenticated":
            return 401
        return 403

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize(
        "role",
        ["read", "write", "admin", "non-contributor", "unauthenticated"],
    )
    def test_status_code__as_user(self, app, registration_status, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.delete_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("registration_status", ["public", "private"])
    @pytest.mark.parametrize(
        "reviews_workflow", [ModerationWorkflows.PRE_MODERATION.value, None]
    )
    def test_status_code__as_moderator(
        self, app, registration_status, reviews_workflow
    ):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status=registration_status,
            schema_response_state=ApprovalStates.IN_PROGRESS,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status=registration_status,
            reviews_workflow=reviews_workflow,
            role="moderator",
        )

        resp = app.delete_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__deleted_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="deleted",
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="deleted",
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.delete_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_status_code__withdrawn_parent(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            registration_status="withdrawn",
            schema_response_state=ApprovalStates.IN_PROGRESS,
            role=role,
        )
        expected_code = self.get_status_code_for_preconditions(
            registration_status="withdrawn",
            reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
            role=role,
        )

        resp = app.delete_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code


@pytest.mark.django_db
class TestSchemaResponseDetailDELETEBehavior:
    """Tests behavior of DELETE requests to the SchemaResponseDetail endpoint.

    Successful DELETE requests should delete the specified SchemaResponse from the database.
    DELETE requests against a SchemaResponse in a state other than IN_PROGRESS should 409.
    """

    @pytest.fixture()
    def schema_response(self, schema_response):
        schema_response.approvals_state_machine.set_state(
            ApprovalStates.IN_PROGRESS
        )
        schema_response.save()
        return schema_response

    def test_DELETE(self, app, schema_response, admin_user):
        app.delete_json_api(
            make_api_url(schema_response), auth=admin_user.auth
        )

        with pytest.raises(
            SchemaResponse.DoesNotExist
        ):  # shows it was really deleted
            schema_response.refresh_from_db()

    @pytest.mark.parametrize("response_state", IMMUTABLE_STATES)
    def test_DELETE_fails_in_unsupported_state(
        self, app, schema_response, admin_user, response_state
    ):
        schema_response.approvals_state_machine.set_state(response_state)
        schema_response.save()
        resp = app.delete_json_api(
            make_api_url(schema_response),
            auth=admin_user.auth,
            expect_errors=True,
        )
        assert resp.status_code == 409


@pytest.mark.django_db
class TestSchemaResponseDetailUnsupportedMethods:
    """Confirm that the SchemaResponseDetail endpoint does not support POST or PUT"""

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_POST(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            role=role
        )
        resp = app.post_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_PUT(self, app, role):
        auth, schema_response, _, _ = configure_permissions_test_preconditions(
            role=role
        )
        resp = app.put_json_api(
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == 405
