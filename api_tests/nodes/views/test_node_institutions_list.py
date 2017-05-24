import pytest

from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import InstitutionFactory, NodeFactory, AuthUserFactory
from api.base.settings.defaults import API_BASE

@pytest.mark.django_db
class TestNodeInstitutionDetail:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.institution = InstitutionFactory()
        self.node = NodeFactory(is_public=True)
        self.node.affiliated_institutions.add(self.institution)
        self.node.save()
        self.user = AuthUserFactory()
        self.node2 = NodeFactory(creator=self.user)

    def test_node_institution_detail(self):

    #   test_return_institution
        url = '/{0}nodes/{1}/institutions/'.format(API_BASE, self.node._id)
        res = self.app.get(url)

        assert res.status_code == 200
        assert res.json['data'][0]['attributes']['name'] == self.institution.name
        assert res.json['data'][0]['id'] == self.institution._id

    #   test_return_no_institution
        url = '/{0}nodes/{1}/institution/'.format(API_BASE, self.node2._id)
        res = self.app.get(
                url, auth=self.user.auth,
                expect_errors=True
        )

        assert res.status_code == 404
