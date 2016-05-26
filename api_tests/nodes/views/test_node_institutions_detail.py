from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, NodeFactory, AuthUserFactory

from api.base.settings.defaults import API_BASE

class TestNodeInstitutionDetail(ApiTestCase):
    def setUp(self):
        super(TestNodeInstitutionDetail, self).setUp()
        self.institution = InstitutionFactory()
        self.node = NodeFactory(is_public=True)
        self.node.primary_institution = self.institution
        self.node.save()
        self.user = AuthUserFactory()
        self.node2 = NodeFactory(creator=self.user)

    def test_return_institution(self):
        url = '/{0}nodes/{1}/institution/'.format(API_BASE, self.node._id)
        res = self.app.get(url)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], self.institution.name)
        assert_equal(res.json['data']['id'], self.institution._id)

    def test_return_no_institution(self):
        url = '/{0}nodes/{1}/institution/'.format(API_BASE, self.node2._id)
        res = self.app.get(
                url, auth=self.user.auth,
                expect_errors=True
        )

        assert_equal(res.status_code, 404)
