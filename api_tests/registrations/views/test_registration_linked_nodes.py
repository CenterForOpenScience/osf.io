import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from website.util import disconnected_from_listeners
from website.project.signals import contributor_removed
from tests.base import ApiTestCase
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import (
    NodeFactory,
    AuthUserFactory,
    RegistrationFactory
)


@pytest.mark.django_db
class TestNodeRelationshipNodeLinks:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.auth = Auth(self.user)
        self.linking_node_source = NodeFactory(creator=self.user)
        self.admin_node = NodeFactory(creator=self.user)
        self.contributor_node = NodeFactory(creator=self.user2)
        self.contributor_node.add_contributor(self.user, auth=Auth(self.user2))
        self.contributor_node.save()
        self.other_node = NodeFactory()
        self.private_node = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True)
        self.linking_node_source.add_pointer(self.private_node, auth=self.auth)
        self.linking_node_source.add_pointer(self.admin_node, auth=self.auth)
        self.public_linking_node_source = NodeFactory(is_public=True, creator=self.user2)
        self.public_linking_node_source.add_pointer(self.private_node, auth=Auth(self.user2))
        self.public_linking_node_source.add_pointer(self.public_node, auth=Auth(self.user2))
        self.public_linking_node = RegistrationFactory(project=self.public_linking_node_source, is_public=True, creator=self.user2)
        self.linking_node = RegistrationFactory(project=self.linking_node_source, creator=self.user)
        self.url = '/{}registrations/{}/relationships/linked_nodes/'.format(API_BASE, self.linking_node._id)
        self.public_url = '/{}registrations/{}/relationships/linked_nodes/'.format(API_BASE, self.public_linking_node._id)

    def payload(self, node_ids=None):
        node_ids = node_ids or [self.admin_node._id]
        env_linked_nodes = [{'type': 'linked_nodes', 'id': node_id} for node_id in node_ids]
        return {'data': env_linked_nodes}

    def test_node_relationship_node_links(self):

    #   get_relationship_linked_nodes
        res = self.app.get(self.url, auth=self.user.auth)

        assert res.status_code == 200
        assert self.linking_node.linked_nodes_self_url in res.json['links']['self']
        assert self.linking_node.linked_nodes_related_url in res.json['links']['html']
        assert self.private_node._id in [e['id'] for e in res.json['data']]

    #   get_linked_nodes_related_counts
        res = self.app.get(
            '/{}registrations/{}/?related_counts=linked_nodes'.format(API_BASE, self.linking_node._id),
            auth=self.user.auth
        )

        assert res.json['data']['relationships']['linked_nodes']['links']['related']['meta']['count'] == 2

    #   get_public_relationship_linked_nodes_logged_out
        res = self.app.get(self.public_url)

        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert self.public_node._id in [e['id'] for e in res.json['data']]

    #   get_public_relationship_linked_nodes_logged_in
        res = self.app.get(self.public_url, auth=self.user.auth)

        assert res.status_code == 200
        assert len(res.json['data']) == 2

    #   get_private_relationship_linked_nodes_logged_out
        res = self.app.get(self.url, expect_errors=True)

        assert res.status_code == 401

    #   post_contributing_node
        res = self.app.post_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   post_public_node
        res = self.app.post_json_api(
            self.url, self.payload([self.public_node._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   post_private_node
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert self.other_node._id not in ids
        assert self.private_node._id in ids

    #   post_mixed_nodes
        res = self.app.post_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert self.other_node._id not in ids
        assert self.contributor_node._id not in ids
        assert self.private_node._id in ids

    #   post_node_already_linked
        res = self.app.post_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   put_contributing_node
        res = self.app.put_json_api(
            self.url, self.payload([self.contributor_node._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   put_private_node
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert self.other_node._id not in ids
        assert self.private_node._id in ids

    #   put_mixed_nodes
        res = self.app.put_json_api(
            self.url, self.payload([self.other_node._id, self.contributor_node._id]),
            auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

        res = self.app.get(
            self.url, auth=self.user.auth
        )

        ids = [data['id'] for data in res.json['data']]
        assert self.other_node._id not in ids
        assert self.contributor_node._id not in ids
        assert self.private_node._id in ids

    #   delete_with_put_empty_array
        payload = self.payload()
        payload['data'].pop()
        res = self.app.put_json_api(
            self.url, payload, auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

    #   delete_one
        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id]),
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = self.app.get(self.url, auth=self.user.auth)

        ids = [data['id'] for data in res.json['data']]
        assert self.admin_node._id in ids
        assert self.private_node._id in ids

    #   delete_multiple

        res = self.app.delete_json_api(
            self.url, self.payload([self.private_node._id, self.admin_node._id]),
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = self.app.get(self.url, auth=self.user.auth)
        assert len(res.json['data']) == 2

    #   delete_not_present
        number_of_links = self.linking_node.linked_nodes.count()
        res = self.app.delete_json_api(
            self.url, self.payload([self.other_node._id]),
            auth=self.user.auth, expect_errors=True
        )
        assert res.status_code == 405

        res = self.app.get(
            self.url, auth=self.user.auth
        )
        assert len(res.json['data']) == number_of_links

    #   node_doesnt_exist
        res = self.app.post_json_api(
            self.url, self.payload(['aquarela']),
            auth=self.user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    #   type_mistyped
        res = self.app.post_json_api(
            self.url,
            {
                'data': [{'type': 'not_linked_nodes', 'id': self.contributor_node._id}]
            },
            auth=self.user.auth,
            expect_errors=True
        )

        assert res.status_code == 405

    #   creates_public_linked_node_relationship_logged_out
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert res.status_code == 401

    #   creates_public_linked_node_relationship_logged_in
        res = self.app.post_json_api(
                self.public_url, self.payload([self.public_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   creates_private_linked_node_relationship_logged_out
        res = self.app.post_json_api(
                self.url, self.payload([self.other_node._id]),
                expect_errors=True
        )

        assert res.status_code == 401

    #   put_public_nodes_relationships_logged_out
        res = self.app.put_json_api(
                self.public_url, self.payload([self.public_node._id]),
                expect_errors=True
        )

        assert res.status_code == 401

    #   put_public_nodes_relationships_logged_in
        res = self.app.put_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

    #   delete_public_nodes_relationships_logged_out
        res = self.app.delete_json_api(
            self.public_url, self.payload([self.public_node._id]),
            expect_errors=True
        )

        assert res.status_code == 401

    #   delete_public_nodes_relationships_logged_in
        res = self.app.delete_json_api(
                self.public_url, self.payload([self.private_node._id]),
                auth=self.user.auth, expect_errors=True
        )

        assert res.status_code == 405

@pytest.mark.django_db
class TestNodeLinkedNodes:

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.app = JSONAPITestApp()
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.linking_node_source = NodeFactory(creator=self.user)
        self.linked_node = NodeFactory(creator=self.user)
        self.linked_node2 = NodeFactory(creator=self.user)
        self.public_node = NodeFactory(is_public=True, creator=self.user)
        self.linking_node_source.add_pointer(self.linked_node, auth=self.auth)
        self.linking_node_source.add_pointer(self.linked_node2, auth=self.auth)
        self.linking_node_source.add_pointer(self.public_node, auth=self.auth)
        self.linking_node_source.save()
        self.linking_node = RegistrationFactory(project=self.linking_node_source, creator=self.user)

        self.url = '/{}registrations/{}/linked_nodes/'.format(API_BASE, self.linking_node._id)
        self.node_ids = list(self.linking_node.nodes_pointer.values_list('guids___id', flat=True))

    def test_linked_nodes_returns_everything(self):
        res = self.app.get(self.url, auth=self.user.auth)

        assert res.status_code == 200
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert len(nodes_returned) == len(self.node_ids)

        for node_id in self.node_ids:
            assert node_id in nodes_returned

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
        new_linking_registration = RegistrationFactory(project=new_linking_node, creator=user)

        res = self.app.get(
            '/{}registrations/{}/linked_nodes/'.format(API_BASE, new_linking_registration._id),
            auth=user.auth
        )

        assert res.status_code == 200
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert len(nodes_returned) == len(self.node_ids)

        for node_id in self.node_ids:
            assert node_id in nodes_returned

        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            self.linked_node2.remove_contributor(user, auth=self.auth)
            self.public_node.remove_contributor(user, auth=self.auth)

        res = self.app.get(
            '/{}registrations/{}/linked_nodes/'.format(API_BASE, new_linking_registration._id),
            auth=user.auth
        )
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert len(nodes_returned) == len(self.node_ids) - 1

        assert self.linked_node._id in nodes_returned
        assert self.public_node._id in nodes_returned
        assert self.linked_node2._id not in nodes_returned

    def test_linked_nodes_doesnt_return_deleted_nodes(self):
        self.linked_node.is_deleted = True
        self.linked_node.save()
        res = self.app.get(self.url, auth=self.user.auth)

        assert res.status_code == 200
        nodes_returned = [linked_node['id'] for linked_node in res.json['data']]
        assert len(nodes_returned) == len(self.node_ids) - 1

        assert self.linked_node._id not in nodes_returned
        assert self.linked_node2._id in nodes_returned
        assert self.public_node._id in nodes_returned

    def test_attempt_to_return_linked_nodes_logged_out(self):
        res = self.app.get(
            self.url, auth=None,
            expect_errors=True
        )

        assert res.status_code == 401
