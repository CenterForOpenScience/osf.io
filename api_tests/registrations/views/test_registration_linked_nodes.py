import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from api_tests.utils import disconnected_from_listeners
from website.project.signals import contributor_removed
from osf_tests.factories import (
    NodeFactory,
    AuthUserFactory,
    RegistrationFactory
)


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeRelationshipNodeLinks:

    @pytest.fixture()
    def contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def auth(self, user):
        return Auth(user)

    @pytest.fixture()
    def private_node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def admin_node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def other_node(self):
        return NodeFactory()

    @pytest.fixture()
    def public_node(self):
        return NodeFactory(is_public=True)

    @pytest.fixture()
    def linking_node_source(self, user, auth, private_node, admin_node):
        linking_node_source = NodeFactory(creator=user)
        linking_node_source.add_pointer(private_node, auth=auth)
        linking_node_source.add_pointer(admin_node, auth=auth)
        return linking_node_source

    @pytest.fixture()
    def contributor_node(self, user, contributor):
        contributor_node = NodeFactory(creator=contributor)
        contributor_node.add_contributor(user, auth=Auth(contributor))
        contributor_node.save()
        return contributor_node

    @pytest.fixture()
    def public_linking_node_source(
            self, contributor, private_node, public_node):
        public_linking_node_source = NodeFactory(
            is_public=True, creator=contributor)
        public_linking_node_source.add_pointer(
            private_node, auth=Auth(contributor))
        public_linking_node_source.add_pointer(
            public_node, auth=Auth(contributor))
        public_linking_node_source.save()
        return public_linking_node_source

    @pytest.fixture()
    def public_linking_node(self, public_linking_node_source, contributor):
        return RegistrationFactory(
            project=public_linking_node_source,
            is_public=True,
            creator=contributor)

    @pytest.fixture()
    def linking_node(self, user, linking_node_source):
        return RegistrationFactory(project=linking_node_source, creator=user)

    @pytest.fixture()
    def url(self, linking_node):
        return '/{}registrations/{}/relationships/linked_nodes/'.format(
            API_BASE, linking_node._id)

    @pytest.fixture()
    def public_url(self, public_linking_node):
        return '/{}registrations/{}/relationships/linked_nodes/'.format(
            API_BASE, public_linking_node._id)

    @pytest.fixture()
    def payload(self, admin_node):
        def payload(node_ids=None):
            node_ids = node_ids or [admin_node._id]
            return {'data': [{'type': 'linked_nodes', 'id': node_id}
                             for node_id in node_ids]}
        return payload

    def test_node_relationship_node_links(
            self, app, user, url, public_url, linking_node,
            private_node, admin_node, public_node,
            contributor_node, other_node, payload):

        #   get_relationship_linked_nodes
        res = app.get(url, auth=user.auth)

        assert res.status_code == 200
        assert linking_node.linked_nodes_self_url in res.json['links']['self']
        assert linking_node.linked_nodes_related_url in res.json['links']['html']
        assert private_node._id in [e['id'] for e in res.json['data']]

    #   get_linked_nodes_related_counts
        res = app.get(
            '/{}registrations/{}/?related_counts=linked_nodes'.format(API_BASE, linking_node._id),
            auth=user.auth
        )

        assert res.json['data']['relationships']['linked_nodes']['links']['related']['meta']['count'] == 2

    #   get_public_relationship_linked_nodes_logged_out
        res = app.get(public_url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert public_node._id in [e['id'] for e in res.json['data']]

    #   get_public_relationship_linked_nodes_logged_in
        res = app.get(public_url, auth=user.auth)

        assert res.status_code == 200
        assert len(res.json['data']) == 2

    #   get_private_relationship_linked_nodes_logged_out
        res = app.get(url, expect_errors=True)

        assert res.status_code == 401

    #   post_contributing_node
        res = app.post_json_api(
            url, payload([contributor_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   post_public_node
        res = app.post_json_api(
            url, payload([public_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   post_private_node
        res = app.post_json_api(
            url, payload([other_node._id]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = app.get(
            url, auth=user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert other_node._id not in ids
        assert private_node._id in ids

    #   post_mixed_nodes
        res = app.post_json_api(
            url, payload([other_node._id, contributor_node._id]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = app.get(
            url, auth=user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert other_node._id not in ids
        assert contributor_node._id not in ids
        assert private_node._id in ids

    #   post_node_already_linked
        res = app.post_json_api(
            url, payload([private_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   put_contributing_node
        res = app.put_json_api(
            url, payload([contributor_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   put_private_node
        res = app.put_json_api(
            url, payload([other_node._id]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = app.get(
            url, auth=user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert other_node._id not in ids
        assert private_node._id in ids

    #   put_mixed_nodes
        res = app.put_json_api(
            url, payload([other_node._id, contributor_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

        res = app.get(
            url, auth=user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert other_node._id not in ids
        assert contributor_node._id not in ids
        assert private_node._id in ids

    #   delete_with_put_empty_array
        new_payload = payload()
        new_payload['data'].pop()
        res = app.put_json_api(
            url, new_payload, auth=user.auth, expect_errors=True
        )
        assert res.status_code == 405

    #   delete_one
        res = app.delete_json_api(
            url, payload([private_node._id]),
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = app.get(url, auth=user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert admin_node._id in ids
        assert private_node._id in ids

    #   delete_multiple

        res = app.delete_json_api(
            url, payload([private_node._id, admin_node._id]),
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 2

    #   delete_not_present
        number_of_links = linking_node.linked_nodes.count()
        res = app.delete_json_api(
            url, payload([other_node._id]),
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = app.get(
            url, auth=user.auth
        )
        assert len(res.json['data']) == number_of_links

    #   node_doesnt_exist
        res = app.post_json_api(
            url, payload(['aquarela']),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    #   type_mistyped
        res = app.post_json_api(
            url,
            {'data': [{
                'type': 'not_linked_nodes',
                'id': contributor_node._id}]},
            auth=user.auth,
            expect_errors=True)

        assert res.status_code == 405

    #   creates_public_linked_node_relationship_logged_out
        res = app.post_json_api(
            public_url, payload([public_node._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   creates_public_linked_node_relationship_logged_in
        res = app.post_json_api(
            public_url, payload([public_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   creates_private_linked_node_relationship_logged_out
        res = app.post_json_api(
            url, payload([other_node._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   put_public_nodes_relationships_logged_out
        res = app.put_json_api(
            public_url, payload([public_node._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   put_public_nodes_relationships_logged_in
        res = app.put_json_api(
            public_url, payload([private_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   delete_public_nodes_relationships_logged_out
        res = app.delete_json_api(
            public_url, payload([public_node._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   delete_public_nodes_relationships_logged_in
        res = app.delete_json_api(
            public_url, payload([private_node._id]),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 405


@pytest.mark.django_db
class TestNodeLinkedNodes:

    @pytest.fixture()
    def auth(self, user):
        return Auth(user)

    @pytest.fixture()
    def private_node_one(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def private_node_two(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_source(
            self, user, auth, private_node_one, private_node_two,
            public_node):
        node_source = NodeFactory(creator=user)
        node_source.add_pointer(private_node_one, auth=auth)
        node_source.add_pointer(private_node_two, auth=auth)
        node_source.add_pointer(public_node, auth=auth)
        node_source.save()
        return node_source

    @pytest.fixture()
    def public_node(self, user):
        return NodeFactory(is_public=True, creator=user)

    @pytest.fixture()
    def linking_node(self, user, node_source):
        return RegistrationFactory(project=node_source, creator=user)

    @pytest.fixture()
    def url(self, linking_node):
        return '/{}registrations/{}/linked_nodes/'.format(
            API_BASE, linking_node._id)

    @pytest.fixture()
    def node_ids(self, linking_node):
        return list(
            linking_node.nodes_pointer.values_list(
                'guids___id', flat=True))

    def test_linked_nodes_returns_everything(self, app, user, url, node_ids):
        res = app.get(url, auth=user.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id']for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids)

        for node_id in node_ids:
            assert node_id in nodes_returned

    def test_linked_nodes_only_return_viewable_nodes(
            self, app, auth, private_node_one, private_node_two,
            public_node, node_ids):
        user = AuthUserFactory()
        new_linking_node = NodeFactory(creator=user)
        private_node_one.add_contributor(user, auth=auth, save=True)
        private_node_two.add_contributor(user, auth=auth, save=True)
        public_node.add_contributor(user, auth=auth, save=True)
        new_linking_node.add_pointer(private_node_one, auth=Auth(user))
        new_linking_node.add_pointer(private_node_two, auth=Auth(user))
        new_linking_node.add_pointer(public_node, auth=Auth(user))
        new_linking_node.save()
        new_linking_registration = RegistrationFactory(
            project=new_linking_node, creator=user)

        res = app.get(
            '/{}registrations/{}/linked_nodes/'.format(API_BASE, new_linking_registration._id),
            auth=user.auth
        )

        assert res.status_code == 200
        nodes_returned = [linked_node['id']
                          for linked_node in res.json['data']]
        assert len(nodes_returned) == len(node_ids)

        for node_id in node_ids:
            assert node_id in nodes_returned

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            private_node_two.remove_contributor(user, auth=auth)
            public_node.remove_contributor(user, auth=auth)

        res = app.get(
            '/{}registrations/{}/linked_nodes/'.format(API_BASE, new_linking_registration._id),
            auth=user.auth
        )
        nodes_returned = [
            linked_node['id'] for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids) - 1

        assert private_node_one._id in nodes_returned
        assert public_node._id in nodes_returned
        assert private_node_two._id not in nodes_returned

    def test_linked_nodes_doesnt_return_deleted_nodes(
            self, app, user, url, private_node_one,
            private_node_two, public_node, node_ids):
        private_node_one.is_deleted = True
        private_node_one.save()
        res = app.get(url, auth=user.auth)

        assert res.status_code == 200
        nodes_returned = [
            linked_node['id'] for linked_node in res.json['data']
        ]
        assert len(nodes_returned) == len(node_ids) - 1

        assert private_node_one._id not in nodes_returned
        assert private_node_two._id in nodes_returned
        assert public_node._id in nodes_returned

    def test_attempt_to_return_linked_nodes_logged_out(self, app, url):
        res = app.get(url, auth=None, expect_errors=True)

        assert res.status_code == 401
