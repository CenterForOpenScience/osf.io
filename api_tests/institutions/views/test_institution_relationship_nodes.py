from nose.tools import *  # flake8: noqa

from framework.auth import Auth

from tests.base import ApiTestCase
from osf_tests.factories import InstitutionFactory, AuthUserFactory, NodeFactory

from api.base.settings.defaults import API_BASE

from website.util import permissions

class TestInstitutionRelationshipNodes(ApiTestCase):
    def setUp(self):
        super(TestInstitutionRelationshipNodes, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.node1 = NodeFactory(creator=self.user)
        self.node2 = NodeFactory(is_public=True)
        self.node3 = NodeFactory()
        self.node1.affiliated_institutions.add(self.institution)
        self.node2.affiliated_institutions.add(self.institution)
        self.node3.affiliated_institutions.add(self.institution)
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
        res = self.app.get(self.institution_nodes_url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        node_ids = [node['id'] for node in res.json['data']]
        assert_in(self.node1._id, node_ids)
        assert_in(self.node2._id, node_ids)
        assert_not_in(self.node3._id, node_ids)

    def test_node_does_not_exist(self):
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload('notIdatAll'),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 404)

    def test_wrong_type(self):
        node = NodeFactory(creator=self.user)
        res = self.app.post_json_api(
            self.institution_nodes_url,
            {'data': [{'type': 'dugtrio', 'id': node._id}]},
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 409)

    def test_user_with_nodes_and_permissions(self):
        node = NodeFactory(creator=self.user)
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert_in(node._id, node_ids)

        node.reload()
        assert_in(self.institution, node.affiliated_institutions.all())

    def test_user_does_not_have_node(self):
        node = NodeFactory()
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)
        node.reload()
        assert_not_in(self.institution, node.affiliated_institutions.all())

    def test_user_is_admin(self):
        node = NodeFactory(creator=self.user)
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 201)
        node.reload()
        assert_in(self.institution, node.affiliated_institutions.all())

    def test_user_is_read_write(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution)
        node = NodeFactory()
        node.add_contributor(user)
        node.save()
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            auth=user.auth
        )

        assert_equal(res.status_code, 201)
        node.reload()
        assert_in(self.institution, node.affiliated_institutions.all())

    def test_user_is_read_only(self):
        user = AuthUserFactory()
        user.affiliated_institutions.add(self.institution)
        node = NodeFactory()
        node.add_contributor(user, permissions=[permissions.READ])
        node.save()

        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)
        node.reload()
        assert_not_in(self.institution, node.affiliated_institutions.all())

    def test_user_is_admin_but_not_affiliated(self):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert_equal(res.status_code, 403)
        node.reload()
        assert_not_in(self.institution, node.affiliated_institutions.all())

    def test_add_some_with_permissions_others_without(self):
        node1 = NodeFactory(creator=self.user)
        node2 = NodeFactory()
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node1._id, node2._id),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)
        node1.reload()
        node2.reload()
        assert_not_in(self.institution, node1.affiliated_institutions.all())
        assert_not_in(self.institution, node2.affiliated_institutions.all())

    def test_add_some_existant_others_not(self):
        assert_in(self.institution, self.node1.affiliated_institutions.all())

        node = NodeFactory(creator=self.user)
        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id, self.node1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)
        node.reload()
        self.node1.reload()
        assert_in(self.institution, self.node1.affiliated_institutions.all())
        assert_in(self.institution, node.affiliated_institutions.all())

    def test_only_add_existent_with_mixed_permissions(self):
        assert_in(self.institution, self.node1.affiliated_institutions.all())
        assert_in(self.institution, self.node2.affiliated_institutions.all())

        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node2._id, self.node1._id),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)
        self.node1.reload()
        self.node2.reload()
        assert_in(self.institution, self.node1.affiliated_institutions.all())
        assert_in(self.institution, self.node2.affiliated_institutions.all())

    def test_only_add_existent_with_permissions(self):
        node = NodeFactory(creator=self.user)
        node.affiliated_institutions.add(self.institution)
        node.save()
        assert_in(self.institution, self.node1.affiliated_institutions.all())
        assert_in(self.institution, node.affiliated_institutions.all())

        res = self.app.post_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id, self.node1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

    def test_delete_user_is_admin(self):
        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node1._id),
            auth=self.user.auth
        )
        self.node1.reload()
        assert_equal(res.status_code, 204)
        assert_not_in(self.institution, self.node1.affiliated_institutions.all())

    def test_delete_user_is_read_write(self):
        self.node3.add_contributor(self.user)
        self.node3.save()

        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node3._id),
            auth=self.user.auth
        )
        self.node3.reload()

        assert_equal(res.status_code, 204)
        assert_not_in(self.institution, self.node3.affiliated_institutions.all())

    def test_delete_user_is_read_only(self):
        self.node3.add_contributor(self.user, permissions='read')
        self.node3.save()

        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node3._id),
            auth=self.user.auth,
            expect_errors=True
        )
        self.node3.reload()

        assert_equal(res.status_code, 403)
        assert_in(self.institution, self.node3.affiliated_institutions.all())

    def test_delete_user_is_admin_and_affiliated_with_inst(self):
        assert_in(self.institution, self.node1.affiliated_institutions.all())

        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node1._id),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)
        self.node1.reload()
        assert_not_in(self.institution, self.node1.affiliated_institutions.all())

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(self.institution)
        node.save()
        assert_in(self.institution, node.affiliated_institutions.all())

        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(node._id),
            auth=user.auth
        )

        assert_equal(res.status_code, 204)
        node.reload()
        assert_not_in(self.institution, node.affiliated_institutions.all())

    def test_delete_user_is_affiliated_with_inst_and_mixed_permissions_on_nodes(self):
        res = self.app.delete_json_api(
            self.institution_nodes_url,
            self.create_payload(self.node1._id, self.node2._id),
            expect_errors=True,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 403)
