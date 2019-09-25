import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf_tests.factories import (
    NodeFactory,
    OSFGroupFactory,
    AuthUserFactory,
    NodeRelationFactory,
)
from osf.utils.permissions import WRITE, READ
from website.project.signals import contributor_removed
from api_tests.utils import disconnected_from_listeners


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeRelationshipNodeLinks:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node_admin(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_contrib(self, user, user_two):
        node_contrib = NodeFactory(creator=user_two)
        node_contrib.add_contributor(user, auth=Auth(user_two))
        node_contrib.save()
        return node_contrib

    @pytest.fixture()
    def node_other(self):
        return NodeFactory()

    @pytest.fixture()
    def node_private(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_public(self):
        return NodeFactory(is_public=True)

    @pytest.fixture()
    def node_linking_private(self, user, node_private):
        node_linking_private = NodeFactory(creator=user)
        node_linking_private.add_pointer(node_private, auth=Auth(user))
        return node_linking_private

    @pytest.fixture()
    def node_linking_public(self, user_two, node_private, node_public):
        node_linking_public = NodeFactory(is_public=True, creator=user_two)
        node_linking_public.add_pointer(node_private, auth=Auth(user_two))
        node_linking_public.add_pointer(node_public, auth=Auth(user_two))
        return node_linking_public

    @pytest.fixture()
    def url_private(self, node_linking_private):
        return '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_linking_private._id)

    @pytest.fixture()
    def url_public(self, node_linking_public):
        return '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_linking_public._id)

    @pytest.fixture()
    def make_payload(self, node_admin):
        def payload(node_ids=None, deprecated_type=True):
            node_ids = node_ids or [node_admin._id]
            env_linked_nodes = [
                {
                    'type': 'linked_nodes' if deprecated_type else 'nodes',
                    'id': node_id
                } for node_id in node_ids]
            return {'data': env_linked_nodes}
        return payload

    def test_get_relationship_linked_nodes(
            self, app, user, node_private, node_public,
            node_linking_private, url_private, url_public):

        #   test_get_relationship_linked_nodes
        res = app.get(url_private, auth=user.auth)

        assert res.status_code == 200

        assert node_linking_private.linked_nodes_self_url in res.json['links']['self']
        assert node_linking_private.linked_nodes_related_url in res.json['links']['html']
        assert res.json['data'][0]['id'] == node_private._id

    #   test_get_public_relationship_linked_nodes_logged_out
        res = app.get(url_public)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == node_public._id

    #   test_get_public_relationship_linked_nodes_logged_in
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2

    #   test_get_private_relationship_linked_nodes_logged_out
        res = app.get(url_private, expect_errors=True)
        assert res.status_code == 401

    #   test_get_private_relationship_linked_nodes_read_group_mem
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_linking_private.add_osf_group(group, READ)
        res = app.get(url_private, auth=group_mem.auth)
        assert res.status_code == 200

    def test_post_contributing_node(
            self, app, user, node_contrib, node_private,
            make_payload, url_private):
        res = app.post_json_api(
            url_private,
            make_payload([node_contrib._id]),
            auth=user.auth
        )

        assert res.status_code == 201

        ids = [data['id'] for data in res.json['data']]
        assert node_contrib._id in ids
        assert node_private._id in ids

    def test_post_public_node(
            self, app, user, node_private, node_public,
            make_payload, url_private):
        res = app.post_json_api(
            url_private,
            make_payload([node_public._id]),
            auth=user.auth
        )

        assert res.status_code == 201

        ids = [data['id'] for data in res.json['data']]
        assert node_public._id in ids
        assert node_private._id in ids

    def test_post_public_node_2_13(
            self, app, user, node_private, node_public,
            make_payload, url_private):
        res = app.post_json_api(
            '{}?version=2.13'.format(url_private),
            make_payload([node_public._id], False),
            auth=user.auth
        )

        assert res.status_code == 201

        ids = [data['id'] for data in res.json['data']]
        assert node_public._id in ids
        assert node_private._id in ids

    def test_post_private_node(
            self, app, user, node_private, node_other,
            node_linking_private, make_payload, url_private):
        res = app.post_json_api(
            url_private,
            make_payload([node_other._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_other._id not in ids
        assert node_private._id in ids

    #   test_group_member_can_post_with_write
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        node_linking_private.add_osf_group(group, READ)
        res = app.post_json_api(
            url_private,
            make_payload([node_other._id]),
            auth=group_mem.auth, expect_errors=True
        )
        assert res.status_code == 403

        node_linking_private.update_osf_group(group, WRITE)
        node_other.add_osf_group(group, WRITE)
        res = app.post_json_api(
            url_private,
            make_payload([node_other._id]),
            auth=group_mem.auth, expect_errors=True
        )
        assert res.status_code == 201

    def test_post_mixed_nodes(
            self, app, user, node_private, node_other,
            node_contrib, make_payload, url_private):
        res = app.post_json_api(
            url_private,
            make_payload([node_other._id, node_contrib._id]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_other._id not in ids
        assert node_contrib._id not in ids
        assert node_private._id in ids

    def test_post_node_already_linked(
            self, app, user, node_private,
            make_payload, url_private):
        res = app.post_json_api(
            url_private,
            make_payload([node_private._id]),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_put_contributing_node(
            self, app, user, node_private, node_contrib,
            make_payload, url_private):
        res = app.put_json_api(
            url_private,
            make_payload([node_contrib._id]),
            auth=user.auth
        )

        assert res.status_code == 200

        ids = [data['id'] for data in res.json['data']]
        assert node_contrib._id in ids
        assert node_private._id not in ids

    def test_put_private_node(
            self, app, user, node_private, node_other,
            make_payload, url_private):
        res = app.put_json_api(
            url_private,
            make_payload([node_other._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_other._id not in ids
        assert node_private._id in ids

    def test_put_mixed_nodes(
            self, app, user, node_private, node_contrib,
            node_other, make_payload, url_private):
        res = app.put_json_api(
            url_private,
            make_payload([node_other._id, node_contrib._id]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403

        res = app.get(url_private, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_other._id not in ids
        assert node_contrib._id not in ids
        assert node_private._id in ids

    def test_delete_with_put_empty_array(
            self, app, user, node_admin, node_linking_private,
            make_payload, url_private):
        node_linking_private.add_pointer(node_admin, auth=Auth(user))
        empty_payload = make_payload()
        empty_payload['data'].pop()
        res = app.put_json_api(
            url_private, empty_payload,
            auth=user.auth
        )
        assert res.status_code == 200
        assert res.json['data'] == empty_payload['data']

    def test_delete_one(
            self, app, user, node_private, node_admin,
            node_linking_private, make_payload, url_private):
        node_linking_private.add_pointer(node_admin, auth=Auth(user))
        res = app.delete_json_api(
            url_private,
            make_payload([node_private._id]),
            auth=user.auth,
        )
        assert res.status_code == 204

        res = app.get(url_private, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert node_admin._id in ids
        assert node_private._id not in ids

    def test_delete_multiple(
            self, app, user, node_private, node_admin,
            node_linking_private, make_payload, url_private):
        node_linking_private.add_pointer(node_admin, auth=Auth(user))
        res = app.delete_json_api(
            url_private,
            make_payload([node_private._id, node_admin._id]),
            auth=user.auth,
        )
        assert res.status_code == 204

        res = app.get(url_private, auth=user.auth)
        assert res.json['data'] == []

    def test_delete_not_present(
            self, app, user, node_other, node_linking_private,
            make_payload, url_private):
        number_of_links = node_linking_private.linked_nodes.count()
        res = app.delete_json_api(
            url_private,
            make_payload([node_other._id]),
            auth=user.auth
        )
        assert res.status_code == 204

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == number_of_links

    def test_delete_invalid_payload(
            self, app, user, node_linking_private, url_private):
        number_of_links = node_linking_private.linked_nodes.count()
        # No id in datum
        payload = {'data': [{'type': 'linked_nodes'}]}
        res = app.delete_json_api(
            url_private, payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        error = res.json['errors'][0]
        assert error['detail'] == 'Request must include /data/id.'

        res = app.get(url_private, auth=user.auth)
        assert len(res.json['data']) == number_of_links

    def test_node_errors(
            self, app, user, node_private, node_contrib,
            node_public, node_other, make_payload,
            url_private, url_public, node_linking_private):

        #   test_node_doesnt_exist
        res = app.post_json_api(
            url_private, make_payload(['aquarela']),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 404

    #   test_type_mistyped
        res = app.post_json_api(
            url_private,
            {
                'data': [{
                    'type': 'not_linked_nodes',
                    'id': node_contrib._id
                }]
            },
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 409

    #   test_type_nodes_not_acceptable_below_2_13
        res = app.post_json_api(
            url_private,
            {
                'data': [{
                    'type': 'nodes',
                    'id': node_contrib._id
                }]
            },
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 409

    #   test_type_linked_nodes_not_acceptable_as_of_2_13
        res = app.post_json_api(
            '{}?version=2.13'.format(url_private),
            {
                'data': [{
                    'type': 'linked_nodes',
                    'id': node_contrib._id
                }]
            },
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 409

    #   test_creates_public_linked_node_relationship_logged_out
        res = app.post_json_api(
            url_public, make_payload([node_public._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   test_creates_public_linked_node_relationship_logged_in
        res = app.post_json_api(
            url_public, make_payload([node_public._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 403

    #   test_creates_private_linked_node_relationship_logged_out
        res = app.post_json_api(
            url_private, make_payload([node_other._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   test_put_public_nodes_relationships_logged_out
        res = app.put_json_api(
            url_public, make_payload([node_public._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   test_put_public_nodes_relationships_logged_in
        res = app.put_json_api(
            url_public, make_payload([node_private._id]),
            auth=user.auth, expect_errors=True
        )

    #   test_put_child_node

        assert res.status_code == 403

    #   test_delete_public_nodes_relationships_logged_out
        res = app.delete_json_api(
            url_public, make_payload([node_public._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   test_delete_public_nodes_relationships_logged_in
        res = app.delete_json_api(
            url_public, make_payload([node_private._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 403

    #   test_node_child_cannot_be_linked_on_create
        node_child = NodeFactory(creator=user)
        node_parent = NodeFactory(creator=user)
        node_parent_child = NodeRelationFactory(child=node_child, parent=node_parent)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_parent_child.parent._id
        )
        res = app.post_json_api(
            url, {
                'data': [{
                    'type': 'linked_nodes',
                    'id': node_parent_child.child._id
                }]
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_linking_node_to_itself _on_create
        node_self = NodeFactory(creator=user)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_self._id
        )
        res = app.post_json_api(
            url_private, make_payload([node_linking_private._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_linking_child_node_to_parent_on_create
        node_child = NodeFactory(creator=user)
        node_parent = NodeFactory(creator=user)
        node_parent_child = NodeRelationFactory(child=node_child, parent=node_parent)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_parent_child.child._id
        )
        res = app.post_json_api(
            url, {
                'data': [{
                    'type': 'linked_nodes',
                    'id': node_parent_child.parent._id
                }]
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_node_child_cannot_be_linked_on_update
        node_child = NodeFactory(creator=user)
        node_parent = NodeFactory(creator=user)
        node_parent_child = NodeRelationFactory(child=node_child, parent=node_parent)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_parent_child.parent._id
        )
        res = app.put_json_api(
            url, {
                'data': [{
                    'type': 'linked_nodes',
                    'id': node_parent_child.child._id
                }]
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_linking_child_node_to_parent_on_update
        node_child = NodeFactory(creator=user)
        node_parent = NodeFactory(creator=user)
        node_parent_child = NodeRelationFactory(child=node_child, parent=node_parent)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_parent_child.child._id
        )
        res = app.put_json_api(
            url, {
                'data': [{
                    'type': 'linked_nodes',
                    'id': node_parent_child.parent._id
                }]
            },
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    #   test_linking_node_to_itself _on_update
        node_self = NodeFactory(creator=user)
        url = '/{}nodes/{}/relationships/linked_nodes/'.format(
            API_BASE, node_self._id
        )
        res = app.put_json_api(
            url_private, make_payload([node_linking_private._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 400

    def test_node_links_and_relationship_represent_same_nodes(
            self, app, user, node_admin, node_contrib, node_linking_private, url_private):
        node_linking_private.add_pointer(node_admin, auth=Auth(user))
        node_linking_private.add_pointer(node_contrib, auth=Auth(user))
        res_relationship = app.get(url_private, auth=user.auth)
        res_node_links = app.get(
            '/{}nodes/{}/node_links/'.format(API_BASE, node_linking_private._id),
            auth=user.auth
        )
        node_links_id = [data['embeds']['target_node']['data']['id']
                         for data in res_node_links.json['data']]
        relationship_id = [data['id']
                           for data in res_relationship.json['data']]

        assert set(node_links_id) == set(relationship_id)


@pytest.mark.django_db
class TestNodeLinkedNodes:

    @pytest.fixture()
    def node_one(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_two(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_public(self, user):
        return NodeFactory(is_public=True, creator=user)

    @pytest.fixture()
    def node_linking(self, user, node_one, node_two, node_public):
        node_linking = NodeFactory(creator=user)
        node_linking.add_pointer(node_one, auth=Auth(user))
        node_linking.add_pointer(node_two, auth=Auth(user))
        node_linking.add_pointer(node_public, auth=Auth(user))
        node_linking.save()
        return node_linking

    @pytest.fixture()
    def url_linked_nodes(self, node_linking):
        return '/{}nodes/{}/linked_nodes/'.format(API_BASE, node_linking._id)

    @pytest.fixture()
    def node_ids(self, node_linking):
        return node_linking.linked_nodes.values_list('guids___id', flat=True)

    def test_linked_nodes_returns_everything(
            self, app, user, node_ids, url_linked_nodes):
        res = app.get(url_linked_nodes, auth=user.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id']for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids)

        for node_id in node_ids:
            assert node_id in nodes_returned

    def test_linked_nodes_returns_everything_2_13(
            self, app, user, node_ids, url_linked_nodes):
        res = app.get('{}?version=2.13'.format(url_linked_nodes), auth=user.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id'] for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids)

        for node_id in node_ids:
            assert node_id in nodes_returned

        node_types = [
            linked_node['type'] for linked_node in res.json['data']
        ]
        assert 'nodes' in node_types
        assert 'linked_nodes' not in node_types

    def test_linked_nodes_only_return_viewable_nodes(
            self, app, user, node_one, node_two, node_public, node_ids):
        user_two = AuthUserFactory()
        node_linking_two = NodeFactory(creator=user_two)
        node_one.add_contributor(user_two, auth=Auth(user), save=True)
        node_two.add_contributor(user_two, auth=Auth(user), save=True)
        node_public.add_contributor(user_two, auth=Auth(user), save=True)
        node_linking_two.add_pointer(node_one, auth=Auth(user_two))
        node_linking_two.add_pointer(node_two, auth=Auth(user_two))
        node_linking_two.add_pointer(node_public, auth=Auth(user_two))
        node_linking_two.save()

        res = app.get(
            '/{}nodes/{}/linked_nodes/'.format(API_BASE, node_linking_two._id),
            auth=user_two.auth
        )

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id']for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids)

        for node_id in node_ids:
            assert node_id in nodes_returned

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            node_two.remove_contributor(user_two, auth=Auth(user))
            node_public.remove_contributor(user_two, auth=Auth(user))

        res = app.get(
            '/{}nodes/{}/linked_nodes/'.format(
                API_BASE, node_linking_two._id
            ),
            auth=user_two.auth
        )
        nodes_returned = [
            linked_node['id']for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids) - 1

        assert node_one._id in nodes_returned
        assert node_public._id in nodes_returned
        assert node_two._id not in nodes_returned

    def test_linked_nodes_doesnt_return_deleted_nodes(
            self, app, user, node_one, node_two, node_public,
            node_ids, url_linked_nodes):
        node_one.is_deleted = True
        node_one.save()
        res = app.get(url_linked_nodes, auth=user.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id'] for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids) - 1

        assert node_one._id not in nodes_returned
        assert node_two._id in nodes_returned
        assert node_public._id in nodes_returned

    def test_attempt_to_return_linked_nodes_logged_out(
            self, app, url_linked_nodes):
        res = app.get(
            url_linked_nodes, auth=None,
            expect_errors=True
        )

        assert res.status_code == 401
