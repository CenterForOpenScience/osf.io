import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    DraftRegistrationFactory,
    AuthUserFactory,
)
from osf.utils.permissions import WRITE


@pytest.mark.django_db
class TestDraftNodeDraftRegistrationsList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def draft_registration(self, user, user_write_contrib):
        draft_reg = DraftRegistrationFactory(
            initiator=user
        )
        draft_reg.add_contributor(
            user_write_contrib,
            permissions=WRITE)
        return draft_reg

    @pytest.fixture()
    def draft_node(self, draft_registration):
        return draft_registration.branched_from

    @pytest.fixture()
    def url_draft_node_draft_registrations(self, draft_node):
        # Specifies version to test functionality when using DraftRegistrationLegacySerializer
        return f'/{API_BASE}draft_nodes/{draft_node._id}/draft_registrations/'

    def test_draft_node_draft_registration_list(
            self, app, user, user_write_contrib, draft_registration, draft_node, url_draft_node_draft_registrations):

        # Un-authorized user does
        res = app.get(url_draft_node_draft_registrations, auth=user_write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # Draft Node and Draft Registration contributor
        res = app.get(url_draft_node_draft_registrations, auth=user.auth)
        assert res.status_code == 200

        data = res.json['data']
        assert len(data) == 1

        returned_draft_reg = data[0]
        assert returned_draft_reg['id'] == draft_registration._id
        assert returned_draft_reg['type'] == 'draft_registrations'

    def test_draft_node_draft_registration_relationship(
            self, app, user, draft_registration, draft_node):

        url = f'/{API_BASE}draft_nodes/{draft_node._id}/'
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        data = res.json['data']
        assert 'draft_registrations' in data['relationships']
