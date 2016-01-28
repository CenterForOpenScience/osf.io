from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from framework.auth import Auth
from api.base.settings.defaults import API_BASE

class TestInstitutionNodeList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionNodeList, self).setUp()
        self.institution = InstitutionFactory()
        self.node1 = NodeFactory(is_public=True)
        self.node1.primary_institution = self.institution
        self.node1.save()
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.node2 = NodeFactory(creator=self.user1, is_public=False)
        self.node2.primary_institution = self.institution
        self.node2.add_contributor(self.user2, auth=Auth(self.user1))
        self.node2.save()
        self.node3 = NodeFactory(creator=self.user2, is_public=False)
        self.node3.primary_institution = self.institution
        self.node3.save()

        self.institution_node_url = '/{0}institutions/{1}/nodes/'.format(API_BASE, self.institution._id)

    def test_return_all_public_nodes(self):
        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.node1._id, ids)
        assert_not_in(self.node2._id, ids)
        assert_not_in(self.node3._id, ids)

    def test_return_private_nodes_with_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.node1._id, ids)
        assert_in(self.node2._id, ids)
        assert_not_in(self.node3._id, ids)

    def test_return_private_nodes_mixed_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user2.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.node1._id, ids)
        assert_in(self.node2._id, ids)
        assert_in(self.node3._id, ids)
