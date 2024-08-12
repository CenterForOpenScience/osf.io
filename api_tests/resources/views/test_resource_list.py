import pytest

from django.utils import timezone

from api_tests.resources.utils import configure_test_auth
from api_tests.utils import UserRoles
from osf.models import Outcome, OutcomeArtifact
from osf.utils.outcomes import ArtifactTypes
from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf_tests.factories import AuthUserFactory, RegistrationFactory

POST_URL = "/v2/resources/"


@pytest.fixture
def admin_user():
    return AuthUserFactory()


@pytest.fixture
def registration(admin_user):
    registration = RegistrationFactory(
        creator=admin_user, is_public=True, has_doi=True
    )
    registration.moderation_state = RegStates.ACCEPTED.db_name
    registration.save()
    return registration


@pytest.fixture
def payload(registration):
    return {
        "data": {
            "type": "resources",
            "relationships": {
                "registration": {
                    "data": {"id": registration._id, "type": "registrations"}
                }
            },
        }
    }


@pytest.mark.django_db
class TestResourceListPOSTPermissions:
    @pytest.mark.parametrize("user_role", UserRoles.write_roles())
    def test_status_code__write_user(
        self, app, registration, payload, user_role
    ):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.post_json_api(
            POST_URL, payload, auth=test_auth, expect_errors=True
        )
        assert resp.status_code == 201

    @pytest.mark.parametrize(
        "user_role", UserRoles.excluding(*UserRoles.write_roles())
    )
    def test_status_code__non_admin(
        self, app, registration, payload, user_role
    ):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.post_json_api(
            POST_URL, payload, auth=test_auth, expect_errors=True
        )
        expected_code = (
            403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("user_role", UserRoles)
    def test_status_code__withdrawn_registration(
        self, app, registration, payload, user_role
    ):
        registration.moderation_state = RegStates.WITHDRAWN.db_name
        registration.save()

        test_auth = configure_test_auth(registration, user_role)
        resp = app.post_json_api(
            POST_URL, payload, auth=test_auth, expect_errors=True
        )
        expected_code = (
            403 if user_role is not UserRoles.UNAUTHENTICATED else 401
        )
        assert resp.status_code == expected_code

    @pytest.mark.parametrize("user_role", UserRoles)
    def test_status_code__deleted_registration(
        self, app, registration, payload, user_role
    ):
        registration.deleted = timezone.now()
        registration.save()

        test_auth = configure_test_auth(registration, UserRoles.ADMIN_USER)
        resp = app.post_json_api(
            POST_URL, payload, auth=test_auth, expect_errors=True
        )
        assert resp.status_code == 410


@pytest.mark.django_db
class TestResourceListPOSTBehavior:
    @pytest.fixture
    def outcome(self, registration):
        return Outcome.objects.for_registration(registration, create=True)

    @pytest.fixture
    def alternate_outcome(self, registration):
        alternate_outcome = Outcome.objects.for_registration(
            registration=RegistrationFactory(has_doi=True)
        )
        alternate_outcome.artifact_metadata.create(
            identifier=registration.get_identifier(category="doi")
        )
        return alternate_outcome

    def test_post_adds_artifact_to_existing_outcome(
        self, app, outcome, registration, admin_user, payload
    ):
        assert outcome.artifact_metadata.count() == 1

        app.post_json_api(
            POST_URL, payload, auth=admin_user.auth, expect_errors=True
        )

        assert outcome.artifact_metadata.count() == 2

    def test_post_creates_outcome_and_primary_artifact_if_none_exists(
        self, app, registration, admin_user, payload
    ):
        assert not OutcomeArtifact.objects.exists()
        assert not Outcome.objects.exists()

        app.post_json_api(
            POST_URL, payload, auth=admin_user.auth, expect_errors=True
        )

        created_outcome = Outcome.objects.for_registration(
            registration, create=False
        )
        assert created_outcome is not None
        assert created_outcome.artifact_metadata.count() == 2

        primary_artifact = created_outcome.artifact_metadata.get(
            artifact_type=ArtifactTypes.PRIMARY
        )
        assert primary_artifact.identifier == registration.get_identifier(
            category="doi"
        )

    def test_post_created_artifact_has_default_metadata(
        self, app, outcome, registration, admin_user, payload
    ):
        app.post_json_api(
            POST_URL, payload, auth=admin_user.auth, expect_errors=True
        )

        created_artifact = outcome.artifact_metadata.order_by(
            "-created"
        ).first()

        assert not created_artifact.title
        assert not created_artifact.description
        assert not created_artifact.identifier
        assert not created_artifact.pid
        assert created_artifact.artifact_type == ArtifactTypes.UNDEFINED
        assert created_artifact.primary_resource_guid == registration._id

    def test_post_adds_artifact_to_primary_outcome_for_registration(
        self, app, outcome, registration, admin_user, payload
    ):
        # Create an outcome where the Registration is *an* artifact but not the *primary* artifact
        alternate_outcome = Outcome.objects.for_registration(
            registration=RegistrationFactory(has_doi=True), create=True
        )
        alternate_outcome.artifact_metadata.create(
            identifier=registration.get_identifier(category="doi")
        )

        assert alternate_outcome.artifact_metadata.count() == 2
        assert outcome.artifact_metadata.count() == 1

        app.post_json_api(
            POST_URL, payload, auth=admin_user.auth, expect_errors=True
        )

        assert alternate_outcome.artifact_metadata.count() == 2
        assert outcome.artifact_metadata.count() == 2

    def test_post_fails_if_no_registration(self, app):
        payload = {"data": {"type": "resources"}}
        resp = app.post_json_api(
            POST_URL, payload, auth=None, expect_errors=True
        )
        assert resp.status_code == 400

    def test_post_fails_with_404_if_registration_does_not_exist(self, app):
        payload = {
            "data": {
                "type": "resources",
                "relationships": {
                    "registration": {
                        "data": {"id": "QWERT", "type": "registrations"}
                    }
                },
            }
        }

        resp = app.post_json_api(
            POST_URL, payload, auth=None, expect_errors=True
        )
        assert resp.status_code == 404

    def test_post_fails_with_409_if_no_registration_identifier(
        self, app, admin_user, payload
    ):
        registration = RegistrationFactory(creator=admin_user, has_doi=False)
        payload["data"]["relationships"]["registration"]["data"]["id"] = (
            registration._id
        )

        resp = app.post_json_api(
            POST_URL, payload, auth=admin_user.auth, expect_errors=True
        )
        assert resp.status_code == 409


@pytest.mark.django_db
class TestResourceListUnsupportedMethods:
    @pytest.mark.parametrize("user_role", UserRoles)
    def test_cannot_GET(self, app, registration, user_role):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.get(POST_URL, auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize("user_role", UserRoles)
    def test_cannot_PUT(self, app, registration, user_role):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.put_json_api(POST_URL, auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize("user_role", UserRoles)
    def test_cannot_PATCH(self, app, registration, user_role):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.patch_json_api(POST_URL, auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize("user_role", UserRoles)
    def test_cannot_DELETE(self, app, registration, user_role):
        test_auth = configure_test_auth(registration, user_role)
        resp = app.delete_json_api(
            POST_URL, auth=test_auth, expect_errors=True
        )
        assert resp.status_code == 405
