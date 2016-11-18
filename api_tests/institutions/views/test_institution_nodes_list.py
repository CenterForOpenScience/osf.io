from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from osf_tests.factories import InstitutionFactory, AuthUserFactory, ProjectFactory, NodeFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionNodeList(ApiTestCase):

    def setUp(self):
        super(TestInstitutionNodeList, self).setUp()
        self.institution = InstitutionFactory()
        self.node1 = ProjectFactory(is_public=True)
        self.node1.affiliated_institutions.add(self.institution)
        self.node1.save()
        self.user1 = AuthUserFactory()
        self.node2 = ProjectFactory(creator=self.user1, is_public=False)
        self.node2.affiliated_institutions.add(self.institution)
        self.node2.save()
        self.node3 = ProjectFactory(is_public=False)
        self.node3.affiliated_institutions.add(self.institution)
        self.node3.save()

        self.institution_node_url = '/{0}institutions/{1}/nodes/'.format(API_BASE, self.institution._id)

    def test_return_all_public_nodes(self):
        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.node1._id, ids)
        assert_not_in(self.node2._id, ids)
        assert_not_in(self.node3._id, ids)

    def test_does_not_return_private_nodes_with_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.node1._id, ids)
        assert_not_in(self.node2._id, ids)
        assert_not_in(self.node3._id, ids)

    def test_affiliated_component_with_affiliated_parent_not_returned(self):
        # version < 2.2
        self.component = NodeFactory(parent=self.node1, is_public=True)
        self.component.affiliated_institutions.add(self.institution)
        self.component.save()
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert_equal(res.status_code, 200)
        assert_in(self.node1._id, affiliated_node_ids)
        assert_not_in(self.component._id, affiliated_node_ids)

    def test_affiliated_component_without_affiliated_parent_not_returned(self):
        # version < 2.2
        self.node = ProjectFactory(is_public=True)
        self.component = NodeFactory(parent=self.node, is_public=True)
        self.component.affiliated_institutions.add(self.institution)
        self.component.save()
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert_equal(res.status_code, 200)
        assert_not_in(self.node._id, affiliated_node_ids)
        assert_not_in(self.component._id, affiliated_node_ids)

    def test_affiliated_component_with_affiliated_parent_returned(self):
        # version 2.2
        self.component = NodeFactory(parent=self.node1, is_public=True)
        self.component.affiliated_institutions.add(self.institution)
        self.component.save()
        url = '{}?version=2.2'.format(self.institution_node_url)
        res = self.app.get(url, auth=self.user1.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert_equal(res.status_code, 200)
        assert_in(self.node1._id, affiliated_node_ids)
        assert_in(self.component._id, affiliated_node_ids)

    def test_affiliated_component_without_affiliated_parent_returned(self):
        # version 2.2
        self.node = ProjectFactory(is_public=True)
        self.component = NodeFactory(parent=self.node, is_public=True)
        self.component.affiliated_institutions.add(self.institution)
        self.component.save()
        url = '{}?version=2.2'.format(self.institution_node_url)
        res = self.app.get(url, auth=self.user1.auth)
        affiliated_node_ids = [node['id'] for node in res.json['data']]
        assert_equal(res.status_code, 200)
        assert_not_in(self.node._id, affiliated_node_ids)
        assert_in(self.component._id, affiliated_node_ids)

