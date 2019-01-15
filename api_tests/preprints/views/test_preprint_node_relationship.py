import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    ProjectFactory,
)

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestPreprintNodeRelationship:
    """
    To unset supplemental node:
    PATCH /preprints/<preprint_id>/relationships/node HTTP/1.1
    Content-Type: application/vnd.api+json
    {
      'data': null
    }
    """

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def supplemental_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/relationships/node/'.format(API_BASE, preprint._id)

    def test_preprint_node_relationship_get(self, app, user, user_two, preprint, supplemental_project, url):
        # For testing purposes
        preprint.is_published = False
        preprint.save()

        # test unauthorized
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # non-contributor
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data'] is None

        preprint.is_published = True
        preprint.node = supplemental_project
        preprint.save()

        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['type'] == 'linked_preprint_nodes'
        assert res.json['data']['id'] == supplemental_project._id
        assert url in res.json['links']['self']

        # No permission to the supplemental node
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['data'] is None

    def test_preprint_node_relationship_create(self, app, user, preprint, supplemental_project, url):
        res = app.post_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_preprint_node_relationship_delete(self, app, user, preprint, supplemental_project, url):
        res = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 405

    def test_preprint_node_relationship_update(self, app, user, user_two, preprint, supplemental_project, url):
        preprint.node = supplemental_project
        preprint.save()

        # test unauthorized
        res = app.patch_json_api(url, expect_errors=True)
        assert res.status_code == 401

        # non-contributor
        res = app.patch_json_api(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # read-contributor
        preprint.add_contributor(user_two, 'read')
        preprint.save()
        res = app.patch_json_api(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # write-contributor
        preprint.update_contributor(user_two, 'write', True, auth=Auth(user), save=True)
        res = app.patch_json_api(url, {'data': None}, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data'] is None
        assert url in res.json['links']['self']
        preprint.reload()
        assert preprint.node is None

        # attempting to add supplemental relationship through this endpoint
        res = app.patch_json_api(url, {'data': {'id': supplemental_project._id, 'type': 'linked_preprint_nodes'}}, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Data must be null. This endpoint can only be used to unset the supplemental project.'
        preprint.reload()
        assert preprint.node is None

        # attempting to patch with empty payload
        res = app.patch_json_api(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'
        preprint.reload()
        assert preprint.node is None
