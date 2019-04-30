import pytest

from osf_tests.factories import InstitutionFactory, NodeFactory, AuthUserFactory, OSFGroupFactory
from osf.utils.permissions import READ
from api.base.settings.defaults import API_BASE


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()

@pytest.mark.django_db
class TestNodeInstitutionList:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def node_one(self, institution):
        node_one = NodeFactory(is_public=True)
        node_one.affiliated_institutions.add(institution)
        node_one.save()
        return node_one

    @pytest.fixture()
    def node_two(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_one_url(self, node_one):
        return self.build_resource_institution_url(node_one)

    @pytest.fixture()
    def node_two_url(self, node_two):
        return self.build_resource_institution_url(node_two)

    def build_resource_institution_url(self, resource):
        return '/{0}{1}s/{2}/institutions/'.format(API_BASE, resource.__class__.__name__.lower(), resource._id)

    def test_node_institution_detail(
        self, app, user, user_two, institution, node_one, node_two, node_one_url, node_two_url,
    ):
        #   test_return_institution
        res = app.get(node_one_url)

        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['name'] == institution.name
        assert res.json['data'][0]['id'] == institution._id

    #   test_return_no_institution
        res = app.get(
            node_two_url, auth=user.auth,
        )
        assert res.status_code == 200
        assert len(res.json['data']) == 0

    #   test_osf_group_member_can_view_node_institutions
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_one.add_osf_group(group, READ)
        res = app.get(node_one_url)
        assert res.status_code == 200

    #   test_non_contrib
        node_one.is_public = False
        node_one.save()
        res = app.get(
            node_one_url, auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403
