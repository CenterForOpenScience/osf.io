import pytest

from osf_tests.factories import InstitutionFactory, NodeFactory, AuthUserFactory, OSFGroupFactory
from api.base.settings.defaults import API_BASE


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeInstitutionDetail:

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

    def test_node_institution_detail(
        self, app, user, institution, node_one, node_two,
    ):

        #   test_return_institution
        url = '/{0}nodes/{1}/institutions/'.format(API_BASE, node_one._id)
        res = app.get(url)

        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['name'] == institution.name
        assert res.json['data'][0]['id'] == institution._id

    #   test_return_no_institution
        url = '/{0}nodes/{1}/institution/'.format(API_BASE, node_two._id)
        res = app.get(
            url, auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 404

    #   test_osf_group_member_can_view_node_institutions
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_one.add_osf_group(group, 'read')
        url = '/{0}nodes/{1}/institutions/'.format(API_BASE, node_one._id)
        res = app.get(url)
        assert res.status_code == 200
