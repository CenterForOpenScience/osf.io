import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NodeLicense
from osf.utils.workflows import CollectionSubmissionStates
from osf_tests.factories import (
    AuthUserFactory,
    CollectionProviderFactory,
    NodeLicenseRecordFactory,
    ProjectFactory,
)


@pytest.mark.django_db
class TestCollectionLicenseEnforcedByProvider:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def cc0(self):
        return NodeLicense.objects.get(name='CC0 1.0 Universal')

    @pytest.fixture()
    def mit(self):
        return NodeLicense.objects.get(name='MIT License')

    @pytest.fixture()
    def provider(self, user, cc0):
        provider = CollectionProviderFactory(creator=user)
        provider.licenses_acceptable.add(cc0)
        return provider

    @pytest.fixture()
    def collection(self, provider):
        return provider.primary_collection

    def make_project(self, user, node_license):
        project = ProjectFactory(creator=user, is_public=True)
        if node_license:
            project.node_license = NodeLicenseRecordFactory(node_license=node_license)
            project.save()
        return project

    def submit(self, app, user, collection, project):
        return app.post_json_api(
            f'/{API_BASE}collections/{collection._id}/collected_metadata/',
            {'data': {'type': 'collected-metadata', 'attributes': {'guid': project._id}}},
            auth=user.auth,
            expect_errors=True,
        )

    def test_submit_with_accepted_license(self, app, user, collection, cc0):
        res = self.submit(app, user, collection, self.make_project(user, cc0))
        assert res.status_code == 201

    def test_submit_with_unaccepted_license_rejected(self, app, user, collection, provider, mit):
        res = self.submit(app, user, collection, self.make_project(user, mit))
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f"The license '{mit.name}' is not accepted by {provider.name}."

    def test_submit_without_license_rejected(self, app, user, collection):
        res = self.submit(app, user, collection, self.make_project(user, None))
        assert res.status_code == 400

    def test_submit_to_unrestricted_provider(self, app, user, collection, provider, mit):
        provider.licenses_acceptable.clear()
        res = self.submit(app, user, collection, self.make_project(user, mit))
        assert res.status_code == 201

    def test_license_change_blocked_while_submission_active(self, app, user, collection, provider, cc0, mit):
        project = self.make_project(user, cc0)
        submission = collection.collect_object(project, user)
        assert submission.machine_state in (
            CollectionSubmissionStates.PENDING.value, CollectionSubmissionStates.ACCEPTED.value,
        )
        payload = {
            'data': {
                'type': 'nodes',
                'id': project._id,
                'attributes': {'node_license': {'year': '2026', 'copyright_holders': ['A']}},
                'relationships': {'license': {'data': {'type': 'licenses', 'id': mit._id}}},
            },
        }
        res = app.patch_json_api(f'/{API_BASE}nodes/{project._id}/', payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'is not accepted by' in res.json['errors'][0]['detail']

        submission.machine_state = CollectionSubmissionStates.REMOVED.value
        submission.save()
        res = app.patch_json_api(f'/{API_BASE}nodes/{project._id}/', payload, auth=user.auth)
        assert res.status_code == 200
