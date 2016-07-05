from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    NodeFactory,
    AuthUserFactory
)
from framework.auth.core import Auth


class TestNodeRelationshipNodeLinks(ApiTestCase):

    def setUp(self):
        super(TestNodeRelationshipNodeLinks, self).setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.auth = Auth(self.user)
        self.linking_node = NodeFactory(creator=self.user)
        self.admin_node = NodeFactory(creator=self.user)
        self.contributor_node = NodeFactory(creator=self.user2)
        self.contributor_node.add_contributor(self.user, auth=Auth(self.user2))
        self.contributor_node.save()
        self.other_node = NodeFactory()
        self.private_node = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True)
        self.linking_node.add_pointer(self.private_node, auth=self.auth)
        self.public_linking_node = NodeFactory(is_public=True, creator=self.user2)
        self.public_linking_node.add_pointer(self.private_node, auth=Auth(self.user2))
        self.public_linking_node.add_pointer(self.public_node, auth=Auth(self.user2))
        self.url = '/{}nodes/{}/relationships/linked_nodes/'.format(API_BASE, self.linking_node._id)
        self.public_url = '/{}nodes/{}/relationships/linked_nodes/'.format(API_BASE, self.public_linking_node._id)

    def payload(self, node_ids=None):
        node_ids = node_ids or [self.admin_node._id]
        env_linked_nodes = [{"type": "linked_nodes", "id": node_id} for node_id in node_ids]
        return {"data": env_linked_nodes}

    def test_get_relationship_linked_nodes(self):
        res = self.app.get(
            self.url, auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        assert_in(self.linking_node.linked_nodes_self_url, res.json['links']['self'])
        assert_in(self.linking_node.linked_nodes_related_url, res.json['links']['html'])
        assert_equal(res.json['data'][0]['id'], self.private_node._id)

    def test_get_public_relationship_linked_nodes_logged_out(self):
        res = self.app.get(self.public_url)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['id'], self.public_node._id)

    def test_get_public_relationship_linked_nodes_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

    def test_get_private_relationship_linked_nodes_logged_out(self):
        res = self.app.get(self.url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_post_contributing_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_public_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.public_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 201)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.public_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_private_node(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_mixed_nodes(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_not_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_post_node_already_linked(self):
        res = self.app.post_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 204)

    def test_put_contributing_node(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.contributor_node._id, ids)
        assert_not_in(self.private_node._id, ids)

    def test_put_private_node(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_put_mixed_nodes(self):
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 403)

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert_not_in(self.other_node._id, ids)
        assert_not_in(self.contributor_node._id, ids)
        assert_in(self.private_node._id, ids)

    def test_delete_with_put_empty_array(self):
        self.linking_node.add_pointer(self.admin_node, auth=self.auth)
        payload = self.payload()
        payload['data'].pop()
        res = self.app.put_json_api(
            self.url, payload,
            auth=self.user.auth
        )
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'], payload['data'])

    def test_delete_one(self):
        self.linking_node.add_pointer(self.admin_node, auth=self.auth)
        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url, auth=self.user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert_in(self.admin_node._id, ids)
        assert_not_in(self.private_node._id, ids)

    def test_delete_multiple(self):
        self.linking_node.add_pointer(self.admin_node, auth=self.auth)
        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id, self.admin_node._id]),
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(self.url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_delete_not_present(self):
        number_of_links = len(self.linking_node.nodes)
        res = self.app.delete_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth
        )
        assert_equal(res.status_code, 204)

        res = self.app.get(
            self.url, auth=self.user.auth
        )
        assert_equal(len(res.json['data']), number_of_links)


    def test_node_doesnt_exist(self):
        res = self.app.post_json_api(
            self.url, self.payload(['aquarela']),
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 404)

    def test_type_mistyped(self):
        res = self.app.post_json_api(
            self.url,
            {
                'data': [{'type': 'not_linked_nodes', 'id': self.contributor_node._id}]
            },
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 409)

    def test_creates_public_linked_node_relationship_logged_out(self):
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_creates_public_linked_node_relationship_logged_in(self):
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_creates_private_linked_node_relationship_logged_out(self):
        res = self.app.post_json_api(
                self.url, self.payload([self.other_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_put_public_nodes_relationships_logged_out(self):
        res = self.app.put_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_put_public_nodes_relationships_logged_in(self):
        res = self.app.put_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_delete_public_nodes_relationships_logged_out(self):
        res = self.app.delete_json_api(
            self.public_url, self.payload([self.public_node._id]),
            expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_delete_public_nodes_relationships_logged_in(self):
        res = self.app.delete_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert_equal(res.status_code, 403)

    def test_node_links_and_relationship_represent_same_nodes(self):
        self.linking_node.add_pointer(self.admin_node, auth=self.auth)
        self.linking_node.add_pointer(self.contributor_node, auth=self.auth)
        res_relationship = self.app.get(
            self.url, auth=self.user.auth
        )
        res_node_links = self.app.get(
            '/{}nodes/{}/node_links/'.format(API_BASE, self.linking_node._id),
            auth=self.user.auth
        )
        node_links_id = [data['embeds']['target_node']['data']['id'] for data in res_node_links.json['data']]
        relationship_id = [data['id'] for data in res_relationship.json['data']]

        assert_equal(set(node_links_id), set(relationship_id))


class TestNodeLinkedNodes(ApiTestCase):
    def setUp(self):
        super(TestNodeLinkedNodes, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.linking_node = NodeFactory(creator=self.user)
        self.linked_node = NodeFactory(creator=self.user)
        self.linked_node2 = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True, creator=self.user)
        self.linking_node.add_pointer(self.linked_node, auth=self.auth)
        self.linking_node.add_pointer(self.linked_node2, auth=self.auth)
        self.linking_node.add_pointer(self.public_node, auth=self.auth)
        self.linking_node.save()
        self.url = '/{}nodes/{}/linked_nodes/'.format(API_BASE, self.linking_node._id)
        self.node_ids = [pointer.node._id for pointer in self.linking_node.nodes_pointer]

    def test_linked_nodes_returns_everything(self):
        res = self.app.get(self.url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids))

        for node_id in self.node_ids:
            assert_in(node_id, nodes_returned)

    def test_linked_nodes_only_return_viewable_nodes(self):
        user = AuthUserFactory()
        new_linking_node = NodeFactory(creator=user)
        self.linked_node.add_contributor(user, auth=self.auth, save=True)
        self.linked_node2.add_contributor(user, auth=self.auth, save=True)
        self.public_node.add_contributor(user, auth=self.auth, save=True)
        new_linking_node.add_pointer(self.linked_node, auth=Auth(user))
        new_linking_node.add_pointer(self.linked_node2, auth=Auth(user))
        new_linking_node.add_pointer(self.public_node, auth=Auth(user))
        new_linking_node.save()

        res = self.app.get(
            '/{}nodes/{}/linked_nodes/'.format(API_BASE, new_linking_node._id),
            auth=user.auth
        )

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids))

        for node_id in self.node_ids:
            assert_in(node_id, nodes_returned)

        self.linked_node2.remove_contributor(user, auth=self.auth)
        self.public_node.remove_contributor(user, auth=self.auth)

        res = self.app.get(
            '/{}nodes/{}/linked_nodes/'.format(API_BASE, new_linking_node._id),
            auth=user.auth
        )
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids) - 1)

        assert_in(self.linked_node._id, nodes_returned)
        assert_in(self.public_node._id, nodes_returned)
        assert_not_in(self.linked_node2._id, nodes_returned)

    def test_linked_nodes_doesnt_return_deleted_nodes(self):
        self.linked_node.is_deleted = True
        self.linked_node.save()
        res = self.app.get(self.url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert_equal(len(nodes_returned), len(self.node_ids) - 1)

        assert_not_in(self.linked_node._id, nodes_returned)
        assert_in(self.linked_node2._id, nodes_returned)
        assert_in(self.public_node._id, nodes_returned)

    def test_attempt_to_return_linked_nodes_logged_out(self):
        res = self.app.get(
            self.url, auth=None,
            expect_errors=True
        )

        assert_equal(res.status_code, 401)
