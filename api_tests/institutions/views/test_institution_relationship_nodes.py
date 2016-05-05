from nose.tools import *

from framework.auth import Auth

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionRelationshipNodes(ApiTestCase):
    def setUp(self):
        super(TestInstitutionRelationshipNodes, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        self.node1 = NodeFactory(creator=self.user)
        self.node2 = NodeFactory(is_public=True)
        self.node3 = NodeFactory()
        self.node1.affiliated_institutions.append(self.institution)
        self.node2.affiliated_institutions.append(self.institution)
        self.node3.affiliated_institutions.append(self.institution)
        self.node1.save()
        self.node2.save()
        self.node3.save()
        self.institution_nodes_url = '/{}institutions/{}/relationships/nodes/'.format(API_BASE, self.institution._id)

    def create_payload(self, *node_ids):
        data = [
            {'type': 'nodes', 'id': id_} for id_ in node_ids
        ]
        return {'data': data}

    def test_get_nodes_no_auth(self):
        res = self.app.get(self.institution_nodes_url)

        assert_equal(res.status_code, 200)
        node_ids = [node['id'] for node in res.json['data']]
        assert_in(self.node2._id, node_ids)
        assert_not_in(self.node1._id, node_ids)
        assert_not_in(self.node3._id, node_ids)

    def test_get_nodes_with_auth(self):
        res = self.app.get(self.institution_nodes_url)

        assert_equal(res.status_code, 200)
        node_ids = [node['id'] for node in res.json['data']]
        assert_in(self.node1._id, node_ids)
        assert_in(self.node2._id, node_ids)
        assert_not_in(self.node3._id, node_ids)
