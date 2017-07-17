import pytest

from api.base.settings.defaults import API_BASE
from framework.auth import Auth
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from website.util import permissions

def make_payload(*node_ids):
    data = [
        {'type': 'nodes', 'id': id_} for id_ in node_ids
    ]
    return {'data': data}

@pytest.mark.django_db
class TestInstitutionRelationshipNodes:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        return user

    @pytest.fixture()
    def node(self, user, institution):
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(institution)
        node.save()
        return node

    @pytest.fixture()
    def node_public(self, user, institution):
        node_public = NodeFactory(is_public=True)
        node_public.affiliated_institutions.add(institution)
        node_public.save()
        return node_public

    @pytest.fixture()
    def node_private(self, user, institution):
        node_private = NodeFactory()
        node_private.affiliated_institutions.add(institution)
        node_private.save()
        return node_private

    @pytest.fixture()
    def url_institution_nodes(self, institution):
        return '/{}institutions/{}/relationships/nodes/'.format(API_BASE, institution._id)


    def test_auth_get_nodes(self, app, institution, user, node, node_public, node_private, url_institution_nodes):
        #test_get_nodes_no_auth
        res = app.get(url_institution_nodes)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node._id not in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

        #test_get_nodes_with_auth
        res = app.get(url_institution_nodes, auth=user.auth)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node._id in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

    def test_node_or_type_does_not_exist(self, app, user, url_institution_nodes):
        #test_node_does_not_exist
        res = app.post_json_api(
            url_institution_nodes,
            make_payload('notIdatAll'),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 404

        #test_node_type_does_not_exist
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            {'data': [{'type': 'dugtrio', 'id': node._id}]},
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 409

    def test_user_with_nodes_and_permissions(self, user, app, url_institution_nodes, institution):
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node._id in node_ids

        node.reload()
        assert institution in node.affiliated_institutions.all()

    def test_user_does_not_have_node(self, app, url_institution_nodes, user, institution):
        node = NodeFactory()
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin(self, app, url_institution_nodes, user, institution):
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )
        assert res.status_code == 201
        node.reload()
        assert institution in node.affiliated_institutions.all()

    def test_user_is_read_write(self, app, url_institution_nodes, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        node = NodeFactory()
        node.add_contributor(user)
        node.save()
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node.reload()
        assert institution in node.affiliated_institutions.all()

    def test_user_is_read_only(self, app, url_institution_nodes, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        node = NodeFactory()
        node.add_contributor(user, permissions=[permissions.READ])
        node.save()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin_but_not_affiliated(self, app, url_institution_nodes, institution):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_add_some_with_permissions_others_without(self, user, app, url_institution_nodes, institution):
        node_one = NodeFactory(creator=user)
        node_two = NodeFactory()
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_one._id, node_two._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node_one.reload()
        node_two.reload()
        assert institution not in node_one.affiliated_institutions.all()
        assert institution not in node_two.affiliated_institutions.all()

    def test_add_some_existant_others_not(self, institution, node, app, url_institution_nodes, user):
        assert institution in node.affiliated_institutions.all()

        node_one= NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_one._id, node._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node.reload()
        node_one.reload()
        assert institution in node.affiliated_institutions.all()
        assert institution in node_one.affiliated_institutions.all()

    def test_only_add_existent_with_mixed_permissions(self, institution, node, node_public, app, url_institution_nodes, user):
        assert institution in node.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_public._id, node._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        node_public.reload()
        assert institution in node.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

    def test_only_add_existent_with_permissions(self, user, node, institution, app, url_institution_nodes):
        node_one = NodeFactory(creator=user)
        node_one.affiliated_institutions.add(institution)
        node_one.save()
        assert institution in node.affiliated_institutions.all()
        assert institution in node_one.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_one._id, node._id),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_admin(self, app, url_institution_nodes, node, user, institution):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )
        node.reload()
        assert res.status_code == 204
        assert institution not in node.affiliated_institutions.all()

    def test_delete_user_is_read_write(self, node_private, user, app, url_institution_nodes, institution):
        node_private.add_contributor(user)
        node_private.save()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_private._id),
            auth=user.auth
        )
        node_private.reload()

        assert res.status_code == 204
        assert institution not in node_private.affiliated_institutions.all()

    def test_delete_user_is_read_only(self, node_private, user, app, url_institution_nodes, institution):
        node_private.add_contributor(user, permissions='read')
        node_private.save()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_private._id),
            auth=user.auth,
            expect_errors=True
        )
        node_private.reload()

        assert res.status_code == 403
        assert institution in node_private.affiliated_institutions.all()

    def test_delete_user_is_admin_and_affiliated_with_inst(self, institution, node, app, url_institution_nodes, user):
        assert institution in node.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self, institution, app, url_institution_nodes):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(institution)
        node.save()
        assert institution in node.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_delete_user_is_affiliated_with_inst_and_mixed_permissions_on_nodes(self, app, url_institution_nodes, node, node_public, user):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node._id, node_public._id),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 403
