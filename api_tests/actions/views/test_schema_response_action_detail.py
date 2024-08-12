import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows
from osf.utils.workflows import ApprovalStates, SchemaResponseTriggers
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
)
from osf_tests.utils import get_default_test_schema


USER_ROLES = [
    "read",
    "write",
    "admin",
    "moderator",
    "non-contributor",
    "unauthenticated",
]
UNAPPROVED_RESPONSE_STATES = [
    state for state in ApprovalStates if state is not ApprovalStates.APPROVED
]
DEFAULT_REVIEWS_WORKFLOW = ModerationWorkflows.PRE_MODERATION.value
DEFAULT_SCHEMA_RESPONSE_STATE = ApprovalStates.APPROVED
DEFAULT_TRIGGER = SchemaResponseTriggers.SUBMIT


def make_api_url(schema_response):
    action = schema_response.actions.last()
    return f"/v2/schema_responses/{schema_response._id}/actions/{action._id}/"


def configure_test_preconditions(
    registration_status="public",
    reviews_workflow=DEFAULT_REVIEWS_WORKFLOW,
    schema_response_state=DEFAULT_SCHEMA_RESPONSE_STATE,
    role="admin",
):
    """Create and Configure a RegistrationProvider, Registration, SchemaResponse, and User."""
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = reviews_workflow
    provider.save()
    registration = RegistrationFactory(
        provider=provider, schema=get_default_test_schema()
    )
    if registration_status == "public":
        registration.is_public = True
    elif registration_status == "private":
        registration.is_public = False
        # set moderation state to a realistic value for a private
        # registration with an approved response
        registration.moderation_state = "embargo"
    elif registration_status == "withdrawn":
        registration.moderation_state = "withdrawn"
    elif registration_status == "deleted":
        registration.deleted = timezone.now()
    registration.save()
    schema_response = registration.schema_responses.last()
    schema_response.actions.create(
        creator=schema_response.initiator,
        from_state=schema_response.reviews_state,
        to_state=schema_response_state.db_name,
        trigger=DEFAULT_TRIGGER.db_name,
    )
    schema_response.approvals_state_machine.set_state(schema_response_state)
    schema_response.save()
    auth = configure_user_auth(registration, role)
    return auth, schema_response, registration, provider


def configure_user_auth(registration, role):
    """Create a user, and assign appropriate permissions for the given role."""
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
class TestSchemaResponseActionDetailGETPermissions:
    """Checks access for GET requests to the RegistrationSchemaResponseList Endpoint.

    GET permissions tests for SchemaResponseActionDetail should exactly mimic
    api_tests/schema_response/views/test_schema_response_detail.py::TestSchemaResponseDetailGETPermissions
    """

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
    def test_GET_status_code__as_user(
        self, app, registration_status, schema_response_state, role
    ):
        auth, schema_response, _, _ = configure_test_preconditions(
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
    def test_GET_status_code__as_moderator(
        self, app, registration_status, schema_response_state, reviews_workflow
    ):
        auth, schema_response, _, _ = configure_test_preconditions(
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
            make_api_url(schema_response), auth=auth, expect_errors=True
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_GET_status_code__deleted_parent(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(
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
    def test_GET_status_code__withdrawn_parent(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(
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
class TestSchemaResponseActionDetailGETBehavior:
    @pytest.fixture()
    def admin_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self, admin_user):
        return RegistrationFactory(user=admin_user)

    @pytest.fixture()
    def schema_response(self, registration):
        return registration.schema_responses.last()

    @pytest.fixture()
    def action(self, schema_response):
        return schema_response.actions.create(
            creator=schema_response.initiator,
            trigger=SchemaResponseTriggers.SUBMIT.db_name,
            from_state=ApprovalStates.IN_PROGRESS.db_name,
            to_state=ApprovalStates.UNAPPROVED.db_name,
        )

    @pytest.fixture()
    def url(self, action):
        return (
            f"/v2/schema_responses/{action.target._id}/actions/{action._id}/"
        )

    def test_schema_response_action_detail(
        self, app, url, action, schema_response, admin_user
    ):
        resp = app.get(url, auth=admin_user.auth)
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == action._id
        assert data["relationships"]["creator"]["data"]["id"] == admin_user._id
        assert (
            data["relationships"]["target"]["data"]["id"]
            == schema_response._id
        )
        assert (
            data["attributes"]["trigger"]
            == SchemaResponseTriggers.SUBMIT.db_name
        )
        assert (
            data["attributes"]["from_state"]
            == ApprovalStates.IN_PROGRESS.db_name
        )
        assert (
            data["attributes"]["to_state"] == ApprovalStates.UNAPPROVED.db_name
        )


@pytest.mark.django_db
class TestSchemaResponseActionDetailUnsupportedMethods:
    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_POST(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.post_json_api(
            make_api_url(schema_response), auth, expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_PUT(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.put_json_api(
            make_api_url(schema_response), auth, expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_PATCH(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.patch_json_api(
            make_api_url(schema_response), auth, expect_errors=True
        )
        assert resp.status_code == 405

    @pytest.mark.parametrize("role", USER_ROLES)
    def test_cannot_DELETE(self, app, role):
        auth, schema_response, _, _ = configure_test_preconditions(role=role)
        resp = app.delete_json_api(
            make_api_url(schema_response), auth, expect_errors=True
        )
        assert resp.status_code == 405
