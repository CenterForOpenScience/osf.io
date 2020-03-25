import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_institutions_list import TestNodeInstitutionList
from osf_tests.factories import DraftRegistrationFactory, AuthUserFactory


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestDraftRegistrationInstitutionList(TestNodeInstitutionList):

    @pytest.fixture()
    def node_one(self, institution, user):
        # Overrides TestNodeInstitutionList
        draft = DraftRegistrationFactory(initiator=user)
        draft.affiliated_institutions.add(institution)
        draft.save()
        return draft

    @pytest.fixture()
    def node_two(self, user):
        # Overrides TestNodeInstitutionList
        return DraftRegistrationFactory(initiator=user)

    @pytest.fixture()
    def node_one_url(self, node_one):
        # Overrides TestNodeInstitutionList
        return '/{}draft_registrations/{}/institutions/'.format(API_BASE, node_one._id)

    @pytest.fixture()
    def node_two_url(self, node_two):
        # Overrides TestNodeInstitutionList
        return '/{}draft_registrations/{}/institutions/'.format(API_BASE, node_two._id)

    # Overrides TestNodeInstitutionList
    def test_node_institution_detail(
        self, app, user, user_two, institution, node_one, node_two, node_one_url, node_two_url,
    ):
        #   test_return_institution_unauthenticated
        res = app.get(node_one_url, expect_errors=True)
        assert res.status_code == 401

        # test_return institution_contrib
        res = app.get(node_one_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['name'] == institution.name
        assert res.json['data'][0]['id'] == institution._id

        #   test_return_no_institution
        res = app.get(
            node_two_url, auth=user.auth,
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        # test non contrib
        res = app.get(
            node_one_url, auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403
