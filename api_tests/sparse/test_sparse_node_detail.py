# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory
)

from api_tests.nodes.views.test_node_contributors_list import NodeCRUDTestCase


@pytest.mark.django_db
class TestSparseNodeDetail:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user2(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def child_node(self, node):
        return NodeFactory(parent=node)

    @pytest.fixture()
    def sparse_url(self, node):
        return f'/v2/sparse/nodes/{node._id}/'

    @pytest.fixture()
    def sparse_url_children(self, node):
        return f'/v2/sparse/nodes/{node._id}/children/'

    def test_get(self, app, user, user2, node, sparse_url):
        resp = app.get(sparse_url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(sparse_url, auth=user2.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(sparse_url, auth=user.auth)
        assert resp.status_code == 200

        data = resp.json['data']
        assert data['attributes']['title'] == node.title

    def test_get_children(self, app, user, user2, child_node, sparse_url_children):
        resp = app.get(sparse_url_children, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(sparse_url_children, auth=user2.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(sparse_url_children, auth=user.auth)
        assert resp.status_code == 200

        data = resp.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['title'] == child_node.title


@pytest.mark.django_db
class TestSparseNodeUpdate(NodeCRUDTestCase):

    @pytest.fixture()
    def sparse_url_public(self, project_public):
        return f'/v2/sparse/nodes/{project_public._id}/'

    @pytest.fixture()
    def make_sparse_node_payload(self):
        def payload(node, attributes, relationships=None):

            payload_data = {
                'data': {
                    'id': node._id,
                    'type': 'sparse-nodes',
                    'attributes': attributes,
                }
            }

            if relationships:
                payload_data['data']['relationships'] = relationships

            return payload_data
        return payload

    def test_update_errors(self, app, user, project_public, sparse_url_public, make_sparse_node_payload):
        #   test_cannot_update_sparse
        res = app.patch_json_api(
            sparse_url_public,
            make_sparse_node_payload(project_public, {'public': False}),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 405


@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
class TestSparseNodeDelete(NodeCRUDTestCase):

    @pytest.fixture()
    def sparse_url_public(self, project_public):
        return f'/v2/sparse/nodes/{project_public._id}/'

    def test_deletes_node_errors(self, app, user, project_public, sparse_url_public):
        #   test_deletes_from_sparse_fails
        res = app.delete_json_api(
            sparse_url_public,
            auth=user.auth,
            expect_errors=True)
        project_public.reload()
        assert res.status_code == 405
        assert project_public.is_deleted is False
        assert 'detail' in res.json['errors'][0]
