import pytest

from api.providers.workflows import Workflows as ModerationWorkflows
from api_tests.utils import UserRoles
from api_tests.resources.utils import configure_test_preconditions

from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf.utils.outcomes import ArtifactTypes
from osf_tests.factories import PrivateLinkFactory


def make_api_url(resource, vol_key=None):
    base_url = f'/v2/resources/{resource._id}/'
    if vol_key:
        return f'{base_url}?view_only={vol_key}'
    return base_url


@pytest.mark.django_db
class TestResourceDetailGETPermissions:

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__public(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.ACCEPTED, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.contributor_roles())
    def test_status_code__unapproved__contributor(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.INITIAL, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.noncontributor_roles())
    def test_status_code__unapproved__non_contributor(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.INITIAL, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403 if test_auth else 401

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', UserRoles.contributor_roles(include_moderator=True))
    def test_status_code__pending_or_embargoed__contributor_or_moderator(self, app, registration_state, user_role):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    def test_status_code__pending_or_embargoed__moderator__unmoderated(self, app, registration_state):
        test_artifact, test_auth, registration = configure_test_preconditions(
            registration_state=registration_state, user_role=UserRoles.MODERATOR
        )
        provider = registration.provider
        provider.reviews_workflow = ModerationWorkflows.NONE.value
        provider.save()

        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403

    @pytest.mark.parametrize('registration_state', [RegStates.PENDING, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', [UserRoles.UNAUTHENTICATED, UserRoles.NONCONTRIB])
    def test_status_code__pending_or_embargoed__noncontrib(self, app, registration_state, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 403 if test_auth else 401

    @pytest.mark.parametrize('registration_state', [RegStates.REJECTED, RegStates.UNDEFINED])
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted(self, app, registration_state, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 410

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__withdrawn(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.WITHDRAWN, user_role=user_role
        )
        resp = app.get(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
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
        resp = app.get(make_api_url(test_artifact, vol_key=vol.key), auth=test_auth, expect_errors=True)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestResourceDetailGETBehavior:

    def test_serialized_data(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()

        resp = app.get(make_api_url(test_artifact), auth=test_auth)
        data = resp.json['data']

        assert data['id'] == test_artifact._id
        assert data['type'] == 'resources'
        assert data['attributes']['resource_type'] == ArtifactTypes(test_artifact.artifact_type).name.lower()
        assert data['attributes']['pid'] == test_artifact.identifier.value
        assert data['relationships']['registration']['data']['id'] == test_artifact.outcome.primary_osf_resource._id

    def test_anonymized_data(self, app):
        test_artifact, test_auth, registration = configure_test_preconditions()
        avol = PrivateLinkFactory(anonymous=True)
        avol.nodes.add(registration)

        resp = app.get(make_api_url(test_artifact, vol_key=avol.key), auth=None)
        data = resp.json['data']
        assert 'pid' not in data['attributes']


@pytest.mark.django_db
class TestResourceDetailUnsupportedMethods:

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
    def test_cannot_DELETEe(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions()
        resp = app.delete_json_api(make_api_url(test_artifact), auth=test_auth, expect_errors=True)
        assert resp.status_code == 405
