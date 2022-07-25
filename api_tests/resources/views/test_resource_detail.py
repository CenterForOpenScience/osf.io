import pytest

from api.providers.workflows import Workflows as ModerationWorkflows
from api_tests.resources.utils import configure_test_preconditions
from api_tests.utils import UserRoles
from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf_tests.factories import PrivateLinkFactory
from osf.utils.outcomes import ArtifactTypes


def make_api_url(resource, vol_key=None):
    base_url = f'/v2/resources/{resource._id}/'
    if vol_key:
        return f'{base_url}?view_only={vol_key}'
    return base_url


def make_patch_payload(
    test_artifact,
    new_pid=None,
    new_title=None,
    new_description=None,
    new_resource_type=None,
    is_finalized=False,
):
    pid = new_pid if new_pid is not None else test_artifact.identifier.value
    title = new_title if new_title is not None else test_artifact.title
    description = new_description if new_description is not None else test_artifact.description
    resource_type = ArtifactTypes(test_artifact.artifact_type).name.lower()
    if new_resource_type is not None:
        resource_type = new_resource_type.name.lower()

    return {
        'data': {
            'id': test_artifact._id,
            'type': 'resources',
            'attributes': {
                'pid': pid,
                'name': title,
                'description': description,
                'resource_type': resource_type,
                'finalized': is_finalized
            }
        }
    }


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
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code

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
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code

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
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code

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
class TestResourceDetailPATCHPermissions:

    @pytest.mark.parametrize('registration_state', [RegStates.ACCEPTED, RegStates.EMBARGO])
    @pytest.mark.parametrize('user_role', UserRoles.write_roles())
    def test_status_code__user_can_write(self, app, registration_state, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.patch_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize('user_role', UserRoles.excluding(*UserRoles.write_roles()))
    def test_status_code__user_cannot_write(self, app, user_role):
        # Only checking the least restrictive state
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.ACCEPTED, user_role=user_role
        )
        resp = app.patch_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('registration_state', [RegStates.REJECTED, RegStates.UNDEFINED])
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted_primary_resource(self, app, registration_state, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.patch_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__withdrawn_primary_resource(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.WITHDRAWN, user_role=user_role
        )
        resp = app.patch_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code


@pytest.mark.django_db
class TestResourceDetailPATCHBehavior:

    @pytest.mark.parametrize('previously_finalized', [True, False])
    def test_patch_standard_fields(self, app, previously_finalized):
        test_artifact, test_auth, _ = configure_test_preconditions()
        test_artifact.finalized = previously_finalized
        test_artifact.save()

        assert not test_artifact.title
        assert not test_artifact.description
        assert test_artifact.artifact_type == ArtifactTypes.DATA

        payload = make_patch_payload(
            test_artifact,
            new_title='New title',
            new_description='This is a description',
            new_resource_type=ArtifactTypes.SUPPLEMENTS,
            is_finalized=previously_finalized
        )
        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth)

        test_artifact.refresh_from_db()
        assert test_artifact.title == 'New title'
        assert test_artifact.description == 'This is a description'
        assert test_artifact.artifact_type == ArtifactTypes.SUPPLEMENTS

    @pytest.mark.parametrize('previously_finalized', [True, False])
    def test_patch_supports_empty_string(self, app, previously_finalized):
        test_artifact, test_auth, _ = configure_test_preconditions()
        test_artifact.title = 'Placeholder'
        test_artifact.description = 'Long placeholder'
        test_artifact.finalized = previously_finalized
        test_artifact.save()

        payload = make_patch_payload(
            test_artifact, new_title='', new_description='', is_finalized=previously_finalized
        )
        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth)

        test_artifact.refresh_from_db()
        assert not test_artifact.title
        assert not test_artifact.description

    def test_patch_pid__updates_identifier(self, app):
        # For futher nuances of update behavior see osf_tests/test_outcomes
        test_artifact, test_auth, _ = configure_test_preconditions()
        original_identifier = test_artifact.identifier

        payload = make_patch_payload(test_artifact, new_pid='updated pid')
        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth)

        test_artifact.refresh_from_db()
        assert test_artifact.identifier != original_identifier
        assert test_artifact.identifier.value == 'updated pid'

    def test_patch_pid__same_pid_no_change(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()
        original_identifier = test_artifact.identifier

        payload = make_patch_payload(test_artifact, new_pid=test_artifact.identifier.value)
        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth)

        test_artifact.refresh_from_db()
        assert test_artifact.identifier == original_identifier
        assert test_artifact.identifier.value == original_identifier.value

    @pytest.mark.xfail(reason='Placeholder, not yet implemented')
    def test_patch_pid__invalid(self, app):
        assert False

    def test_patch_finalized__valid_resource(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()
        assert test_artifact.identifier.value
        assert test_artifact.artifact_type

        payload = make_patch_payload(test_artifact, is_finalized=True)
        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth)

        test_artifact.refresh_from_db()
        assert test_artifact.finalized

    def test_patch_finalized__cannot_revert(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()
        test_artifact.finalized = True
        test_artifact.save()

        payload = make_patch_payload(test_artifact, is_finalized=False)
        resp = app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth, expect_errors=True)

        assert resp.status_code == 409
        error_info = resp.json['errors'][0]
        assert error_info['source']['pointer'] == '/data/attributes/finalized'

    @pytest.mark.parametrize(
        'missing_pid, missing_resource_type, expected_error_source',
        [
            (True, False, '/data/attributes/pid'),
            (False, True, '/data/attributes/resource_type'),
            (True, True, '/data/attributes/'),
        ]
    )
    @pytest.mark.parametrize('previously_finalized', [True, False])
    def test_patch_finalized__missing_required_fields(
        self, app, missing_pid, missing_resource_type, expected_error_source, previously_finalized
    ):
        test_artifact, test_auth, _ = configure_test_preconditions()
        if missing_pid:
            identifier = test_artifact.identifier
            identifier.value = ''
            identifier.save()
        if missing_resource_type:
            test_artifact.artifact_type = ArtifactTypes.UNDEFINED
        test_artifact.finalized = previously_finalized
        test_artifact.save()

        payload = make_patch_payload(test_artifact, is_finalized=True)
        resp = app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth, expect_errors=True)

        assert resp.status_code == 409
        error_info = resp.json['errors'][0]
        assert error_info['source']['pointer'] == expected_error_source

    def test_patch_finalized__patch_is_atomic(self, app):
        test_artifact, test_auth, _ = configure_test_preconditions()
        test_artifact.artifact_type = ArtifactTypes.UNDEFINED
        test_artifact.save()

        original_title = test_artifact.title
        original_description = test_artifact.description
        original_identifier = test_artifact.identifier

        payload = make_patch_payload(
            test_artifact,
            new_title='Some new name',
            new_description='Some new desciprtion',
            new_pid='Some new pid',
            new_resource_type=ArtifactTypes.UNDEFINED,
            is_finalized=True
        )

        app.patch_json_api(make_api_url(test_artifact), payload, auth=test_auth, expect_errors=True)
        test_artifact.refresh_from_db()

        assert test_artifact.title == original_title
        assert test_artifact.description == original_description
        assert test_artifact.artifact_type == ArtifactTypes.UNDEFINED
        assert test_artifact.identifier == original_identifier
        assert test_artifact.identifier.value == original_identifier.value
        assert not test_artifact.finalized


@pytest.mark.django_db
class TestResourceDetailDELETEPermissions:

    @pytest.mark.parametrize('registration_state', [RegStates.ACCEPTED, RegStates.EMBARGO])
    def test_status_code__admin(self, app, registration_state):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=UserRoles.ADMIN
        )
        resp = app.delete_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 204

    @pytest.mark.parametrize('user_role', UserRoles.excluding(UserRoles.ADMIN_USER))
    def test_status_code__non_admin(self, app, user_role):
        # Only checking the least restrictive state
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.ACCEPTED, user_role=user_role
        )
        resp = app.delete_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code

    @pytest.mark.parametrize('registration_state', [RegStates.REJECTED, RegStates.UNDEFINED])
    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__deleted_primary_resource(self, app, registration_state, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=registration_state, user_role=user_role
        )
        resp = app.delete_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        assert resp.status_code == 410

    @pytest.mark.parametrize('user_role', UserRoles)
    def test_status_code__withdrawn_primary_resource(self, app, user_role):
        test_artifact, test_auth, _ = configure_test_preconditions(
            registration_state=RegStates.WITHDRAWN, user_role=user_role
        )
        resp = app.delete_json_api(
            make_api_url(test_artifact),
            make_patch_payload(test_artifact),
            auth=test_auth,
            expect_errors=True
        )
        expected_status_code = 403 if test_auth else 401
        assert resp.status_code == expected_status_code


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
