import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows
from api_tests.resources.utils import configure_test_preconditions
from api_tests.utils import UserRoles
from osf.models import Outcome
from osf.utils.outcomes import ArtifactTypes
from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf_tests.factories import (
    AuthUserFactory,
    IdentifierFactory,
    PrivateLinkFactory,
    RegistrationFactory,
)


def make_api_url(registration, vol_key=None, query_filters=None):
    base_url = f'/v2/registrations/{registration._id}/resources/'
    if vol_key:
        return f'{base_url}?view_only={vol_key}'
    return base_url


@pytest.mark.django_db
class TestRegistrationResourceListGETPermissions:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__public(self, app, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=RegStates.ACCEPTED, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.contributor_roles())
    def test_status_code__unapproved__contributor(self, app, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=RegStates.INITIAL, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.noncontributor_roles())
    def test_status_code__unapproved__non_contributor(self, app, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=RegStates.INITIAL, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403 if test_auth else 401

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', UserRoles.contributor_roles(include_moderator=True))
    def test_status_code__pending_or_embargoed__contributor_or_moderator(self, app, registration_state, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    def test_status_code__pending_or_embargoed__moderator__unmoderated(self, app, registration_state):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=UserRoles.MODERATOR
        )
        provider = registration.provider
        provider.reviews_workflow = ModerationWorkflows.NONE.value
        provider.save()

        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_status_code__pending_or_embargoed__noncontrib(self, app, registration_state, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403 if test_auth else 401

    @pytest.mark.parametrize('registration_state', [RegStates.REJECTED, RegStates.UNDEFINED])
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted(self, app, registration_state, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 410

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__withdrawn(self, app, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=RegStates.WITHDRAWN, user_role=user_role
        )
        resp = app.get(make_api_url(registration), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403 if test_auth else 401

    @pytest.mark.parametrize('registration_state', [RegStates.INITIAL, RegStates.PENDING, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', UserRoles.noncontributor_roles())
    def test_status_code__vol(self, app, registration_state, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        provider = registration.provider
        provider.reviews_workflow = ModerationWorkflows.NONE.value
        provider.save()

        vol = PrivateLinkFactory(anonymous=False)
        vol.nodes.add(registration)
        resp = app.get(make_api_url(registration, vol_key=vol.key), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestRegistrationResourceListGETBehavior:

    @pytest.fixture
    def admin_user(self):
        return AuthUserFactory()

    @pytest.fixture
    def registration(self, admin_user):
        return RegistrationFactory(creator=admin_user, has_doi=True)

    @pytest.fixture
    def outcome(self, registration):
        return Outcome.objects.for_registration(registration, create=True)

    @pytest.fixture
    def artifact_one(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.DATA,
            finalized=True
        )

    @pytest.fixture
    def artifact_two(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.ANALYTIC_CODE,
            finalized=True
        )

    @pytest.fixture
    def draft_artifact(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.MATERIALS,
            finalized=False
        )

    @pytest.fixture
    def deleted_artifact(self, outcome):
        return outcome.artifact_metadata.create(
            identifier=IdentifierFactory(),
            artifact_type=ArtifactTypes.PAPERS,
            finalized=True,
            deleted=timezone.now()
        )

    def test_visibility(
        self, app, registration, artifact_one, artifact_two, draft_artifact, deleted_artifact, admin_user
    ):
        # Only artifacts with `finalized=True` and `deleted=None` should appear.
        resp = app.get(make_api_url(registration), auth=admin_user.auth)
        returned_ids = {entry['id'] for entry in resp.json['data']}
        assert returned_ids == {artifact_one._id, artifact_two._id}

    def test_anonymized_data(self, app, registration, artifact_one, admin_user):
        avol = PrivateLinkFactory(anonymous=True)
        avol.nodes.add(registration)

        resp = app.get(make_api_url(registration, vol_key=avol.key), auth=admin_user.auth)
        data = resp.json['data'][0]
        assert 'pid' not in data['attributes']
        assert 'resource_type' in data['attributes']
        assert 'description' in data['attributes']

    def test_self_link_contains_vol_key(self, app, registration, artifact_one):
        avol = PrivateLinkFactory(anonymous=True)
        avol.nodes.add(registration)

        resp = app.get(make_api_url(registration, vol_key=avol.key), auth=None)
        assert resp.json['data'][0]['links']['self'].endswith(avol.key)

    def test_filtering(self, app, registration, artifact_one, artifact_two, admin_user):
        base_url = make_api_url(registration)
        filter_url = f'{base_url}?filter[resource_type]=analytic_code'

        resp = app.get(filter_url, auth=admin_user.auth)
        data = resp.json['data']
        assert len(data) == 1
        assert data[0]['id'] == artifact_two._id


@pytest.mark.django_db
class TestRegistrationResourceListUnsupportedMethods:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_POST(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions()
        resp = app.post_json_api(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PUT(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions()
        resp = app.put_json_api(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_PATCH(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions()
        resp = app.patch_json_api(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_cannot_DELETE(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions()
        resp = app.delete_json_api(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 405
