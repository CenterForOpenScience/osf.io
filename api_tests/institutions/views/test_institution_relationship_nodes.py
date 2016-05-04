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
        self.node2 = NodeFactory(creator=self.user)
        self.institution_nodes_url = '/{}institutions/{1}/relationships/nodes/'.format(API_BASE. self.institution._id)

    def create_payload(self, *node_ids):
        data = [
            {'type': 'nodes', 'id': id_} for id_ in node_ids
        ]
        return {'data': data}

