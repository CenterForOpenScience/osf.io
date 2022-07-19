import pytest

from django.utils import timezone

from api.providers.workflows import Workflows as ModerationWorkflows
from api_tests.utils import UserRoles
from osf.models import Outcome
from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf_tests.factories import (
    AuthUserFactory,
    PrivateLinkFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)
from osf.utils.outcomes import ArtifactTypes
from api.outputs import urls, permissions, views, serializers  # noqa

TEST_EXTERNAL_PID = 'This is a doi'

# Omitted the following redundant states:
# PENDING_EMBARGO_TERMINATION (overlaps EMBARGO)
# PENDING_WITHDRAW_REQESST and PENDING_WITHDRAW (ovrlaps ACCEPTED)
# REVERTED (overlaps REJECTED)
#
# Techncically PENDING and EMBARGO overlap as well, but worth confirming EMBARGO behavior
STATE_VISIBILITY_MAPPINGS = {
    RegStates.INITIAL: {'public': False, 'deleted': False},
    RegStates.PENDING: {'public': False, 'deleted': False},
    RegStates.EMBARGO: {'public': False, 'deleted': False},
    RegStates.ACCEPTED: {'public': True, 'deleted': False},
    RegStates.WITHDRAWN: {'public': True, 'deleted': False},
    RegStates.REJECTED: {'public': False, 'deleted': True},
    # Use the generally unreachable UNDEFINED value for the edge case of deleted and public
    RegStates.UNDEFINED: {'public': True, 'deleted': True},
}


def make_api_url(output, vol_key=None):
    base_url = f'/v2/outputs/{output._id}/'
    if vol_key:
        return f'{base_url}?view_only={vol_key}'
    return base_url

def configure_test_preconditions(registration_state=RegStates.ACCEPTED, user_role=UserRoles.ADMIN_USER):
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION.value
    provider.save()

    state_settings = STATE_VISIBILITY_MAPPINGS[registration_state]
    registration = RegistrationFactory(
        provider=provider,
        is_public=state_settings['public'],
        has_doi=True
    )
    registration.moderation_state = registration_state.db_name
    registration.deleted = timezone.now() if state_settings['deleted'] else None
    registration.save()

    outcome = Outcome.objects.for_registration(registration, create=True)
    test_artifact = outcome.add_artifact_by_pid(
        pid=TEST_EXTERNAL_PID, artifact_type=ArtifactTypes.DATA, create_identifier=True
    )

    test_auth = _configure_permissions_test_auth(registration, user_role)

    return test_artifact, test_auth, registration


def _configure_permissions_test_auth(registration, user_role):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        registration.provider.get_group('moderator').user_set.add(user)
    elif user_role in UserRoles.contributor_roles():
        registration.add_contributor(user, user_role.get_permissions_string())

    return user.auth


@pytest.mark.django_db
class TestOutputDetailGETPermissions:

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


@pytest.mark.django_db
class TestOutputDetailGETBehavior:

    def test_serialized_data(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()

        resp = app.get(make_api_url(test_artifact), auth=test_auth)
        data = resp.json['data']
        print(data)

        assert data['id'] == test_artifact._id
        assert data['type'] == 'outputs'
        assert data['attributes']['output_type'] == ArtifactTypes(test_artifact.artifact_type).name.lower()
        assert data['attributes']['pid'] == test_artifact.identifier.value
        assert data['relationships']['registration']['data']['id'] == test_artifact.outcome.primary_osf_resource._id

    def test_anonymized_data(self, app):
        test_artifact, test_auth, registration = configure_test_preconditions()
        avol = PrivateLinkFactory(anonymous=True)
        avol.nodes.add(registration)

        url = make_api_url(test_artifact, vol_key=avol.key)
        print(url)
        resp = app.get(make_api_url(test_artifact, vol_key=avol.key), auth=None)
        data = resp.json['data']
        assert 'pid' not in data['attributes']
