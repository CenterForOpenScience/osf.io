import pytest

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    DraftRegistrationFactory,
    AuthUserFactory,
    ProjectFactory
)


@pytest.mark.django_db
class TestDraftNodeDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    def test_detail_response(self, app, user, user_two):
        draft_reg = DraftRegistrationFactory(initiator=user)
        draft_reg.add_contributor(user_two)
        draft_reg.save()

        draft_node = draft_reg.branched_from

        # Unauthenticated
        url = '/{}draft_nodes/{}/'.format(API_BASE, draft_node._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # Draft Node and Draft Registration contributor
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # Draft Registration contributor only
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200
        data = res.json['data']

        assert data['attributes'] == {}
        assert data['type'] == 'draft-nodes'
        assert data['id'] == draft_node._id

        assert url + 'files/' in data['relationships']['files']['links']['related']['href']
        assert url in data['links']['self']

        # assert cannot access node through this endpoint
        project = ProjectFactory(creator=user)
        url = '/{}draft_nodes/{}/'.format(API_BASE, project._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

        # cannot access draft node after it's been registered (it's now a node!)
        draft_reg.register(Auth(user))
        url = '/{}draft_nodes/{}/'.format(API_BASE, draft_node._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404
