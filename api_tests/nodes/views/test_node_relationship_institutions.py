import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from osf.utils import permissions


@pytest.mark.django_db
class TestNodeRelationshipInstitutions:

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_two(self):
        return InstitutionFactory()

    @pytest.fixture()
    def write_contrib_institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def read_contrib_institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def resource_factory(self):
        return NodeFactory

    @pytest.fixture()
    def make_resource_url(self):
        def make_resource_url(node):
            return '/{0}nodes/{1}/relationships/institutions/'.format(
                API_BASE, node._id)
        return make_resource_url

    @pytest.fixture()
    def user(self, institution_one, institution_two):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution_one)
        user.affiliated_institutions.add(institution_two)
        user.save()
        return user

    @pytest.fixture()
    def write_contrib(self, write_contrib_institution):
        write_contrib = AuthUserFactory()
        write_contrib.affiliated_institutions.add(write_contrib_institution)
        write_contrib.save()
        return write_contrib

    @pytest.fixture()
    def read_contrib(self, read_contrib_institution):
        read_contrib = AuthUserFactory()
        read_contrib.affiliated_institutions.add(read_contrib_institution)
        read_contrib.save()
        return read_contrib

    @pytest.fixture()
    def node(self, user, write_contrib, read_contrib):
        node = NodeFactory(creator=user)
        node.add_contributor(
            write_contrib,
            permissions=permissions.WRITE)
        node.add_contributor(read_contrib, permissions=permissions.READ)
        node.save()
        return node

    @pytest.fixture()
    def node_institutions_url(self, node):
        return '/{0}nodes/{1}/relationships/institutions/'.format(
            API_BASE, node._id)

    @pytest.fixture()
    def create_payload(self):
        def payload(*institution_ids):
            data = []
            for id_ in institution_ids:
                data.append({'type': 'institutions', 'id': id_})
            return {'data': data}
        return payload

    def test_node_errors(
            self, app, user, institution_one, resource_factory,
            create_payload, node_institutions_url):

        #   test_node_with_no_permissions
        unauthorized_user = AuthUserFactory()
        unauthorized_user.affiliated_institutions.add(institution_one)
        unauthorized_user.save()
        res = app.put_json_api(
            node_institutions_url,
            create_payload([institution_one._id]),
            auth=unauthorized_user.auth,
            expect_errors=True,
        )
        assert res.status_code == 403

    #   test_user_with_no_institution
        unauthorized_user = AuthUserFactory()
        res = app.put_json_api(node_institutions_url,
            create_payload(institution_one._id),
            expect_errors=True,
            auth=unauthorized_user.auth
        )
        assert res.status_code == 403

    #   test_institution_does_not_exist
        res = app.put_json_api(
            node_institutions_url,
            create_payload('not_an_id'),
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 404

    #   test_wrong_type
        res = app.put_json_api(
            node_institutions_url,
            {'data': [{'type': 'not_institution', 'id': institution_one._id}]},
            expect_errors=True,
            auth=user.auth
        )

        assert res.status_code == 409

    #   test_remove_institutions_with_no_permissions
        res = app.put_json_api(
            node_institutions_url,
            create_payload(),
            expect_errors=True
        )
        assert res.status_code == 401

    #   test_retrieve_private_node_no_auth
        res = app.get(node_institutions_url, expect_errors=True)
        assert res.status_code == 401

    def test_get_public_node(self, app, node, node_institutions_url):
        node.is_public = True
        node.save()

        res = app.get(
            node_institutions_url
        )

        assert res.status_code == 200
        assert res.json['data'] == []

    def test_user_with_institution_and_permissions(
            self, app, user, institution_one,
            institution_two, node, node_institutions_url, create_payload):
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.post_json_api(
            node_institutions_url,
            create_payload(institution_one._id, institution_two._id),
            auth=user.auth
        )

        assert res.status_code == 201
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert institution_one._id in ret_institutions
        assert institution_two._id in ret_institutions

        node.reload()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_user_with_institution_and_permissions_through_patch(
            self, app, user, institution_one, institution_two,
            node, node_institutions_url, create_payload):
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.put_json_api(
            node_institutions_url,
            create_payload(institution_one._id, institution_two._id),
            auth=user.auth
        )

        assert res.status_code == 200
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert institution_one._id in ret_institutions
        assert institution_two._id in ret_institutions

        node.reload()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_remove_institutions_with_affiliated_user(
            self, app, user, institution_one, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        res = app.put_json_api(
            node_institutions_url,
            {'data': []},
            auth=user.auth
        )

        assert res.status_code == 200
        node.reload()
        assert node.affiliated_institutions.count() == 0

    def test_using_post_making_no_changes_returns_204(
            self, app, user, institution_one,
            node, node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        res = app.post_json_api(
            node_institutions_url,
            create_payload(institution_one._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node.reload()
        assert institution_one in node.affiliated_institutions.all()

    def test_put_not_admin_but_affiliated(
            self, app, institution_one,
            node, node_institutions_url,
            create_payload):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution_one)
        user.save()
        node.add_contributor(user)
        node.save()

        res = app.put_json_api(
            node_institutions_url,
            create_payload(institution_one._id),
            auth=user.auth
        )

        node.reload()
        assert res.status_code == 200
        assert institution_one in node.affiliated_institutions.all()

    def test_add_through_patch_one_inst_to_node_with_inst(
            self, app, user, institution_one, institution_two,
            node, node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.patch_json_api(
            node_institutions_url,
            create_payload(institution_one._id, institution_two._id),
            auth=user.auth
        )

        assert res.status_code == 200
        node.reload()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_add_through_patch_one_inst_while_removing_other(
            self, app, user, institution_one, institution_two,
            node, node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.patch_json_api(
            node_institutions_url,
            create_payload(institution_two._id),
            auth=user.auth
        )

        assert res.status_code == 200
        node.reload()
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_add_one_inst_with_post_to_node_with_inst(
            self, app, user, institution_one, institution_two,
            node, node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.post_json_api(
            node_institutions_url,
            create_payload(institution_two._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node.reload()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_delete_nothing(
            self, app, user, node_institutions_url, create_payload):
        res = app.delete_json_api(
            node_institutions_url,
            create_payload(),
            auth=user.auth
        )
        assert res.status_code == 204

    def test_delete_existing_inst(
            self, app, user, institution_one, node,
            node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        res = app.delete_json_api(
            node_institutions_url,
            create_payload(institution_one._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node.reload()
        assert institution_one not in node.affiliated_institutions.all()

    def test_delete_not_affiliated_and_affiliated_insts(
            self, app, user, institution_one, institution_two,
            node, node_institutions_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.delete_json_api(
            node_institutions_url,
            create_payload(institution_one._id, institution_two._id),
            auth=user.auth,
        )

        assert res.status_code == 204
        node.reload()
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

    def test_delete_user_is_admin(
            self, app, user, institution_one, node,
            make_resource_url, create_payload):
        node.affiliated_institutions.add(institution_one)
        node.save()

        url = make_resource_url(node)

        res = app.delete_json_api(
            url,
            create_payload(institution_one._id),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_read_write(
            self, app, institution_one, node,
            node_institutions_url, create_payload):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution_one)
        user.save()
        node.add_contributor(user)
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            node_institutions_url,
            create_payload(institution_one._id),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_read_only(
            self, app, institution_one, node,
            node_institutions_url, create_payload):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution_one)
        user.save()
        node.add_contributor(user, permissions=permissions.READ)
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            node_institutions_url,
            create_payload(institution_one._id),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403

    def test_delete_user_is_admin_but_not_affiliated_with_inst(
            self, app, institution_one, resource_factory, create_payload, make_resource_url):
        user = AuthUserFactory()
        node = resource_factory(creator=user)
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        url = make_resource_url(node)
        res = app.delete_json_api(
            url,
            create_payload(institution_one._id),
            auth=user.auth,
        )

        assert res.status_code == 204
        node.reload()
        assert institution_one not in node.affiliated_institutions.all()

    def test_admin_can_add_affiliated_institution(
            self, app, user, institution_one, node, node_institutions_url):
        payload = {
            'data': [{
                'type': 'institutions',
                'id': institution_one._id
            }]
        }
        res = app.post_json_api(node_institutions_url, payload, auth=user.auth)
        node.reload()
        assert res.status_code == 201
        assert institution_one in node.affiliated_institutions.all()

    def test_admin_can_remove_admin_affiliated_institution(
            self, app, user, institution_one, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        payload = {
            'data': [{
                'type': 'institutions',
                'id': institution_one._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url, payload, auth=user.auth)
        node.reload()
        assert res.status_code == 204
        assert institution_one not in node.affiliated_institutions.all()

    def test_admin_can_remove_read_write_contributor_affiliated_institution(
            self, app, user, read_contrib_institution, node, node_institutions_url):
        node.affiliated_institutions.add(read_contrib_institution)
        node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': read_contrib_institution._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url, payload, auth=user.auth)
        node.reload()
        assert res.status_code == 204
        assert read_contrib_institution not in node.affiliated_institutions.all()

    def test_read_write_contributor_can_add_affiliated_institution(
            self, app, write_contrib, write_contrib_institution, node, node_institutions_url):
        payload = {
            'data': [{
                'type': 'institutions',
                'id': write_contrib_institution._id
            }]
        }
        res = app.post_json_api(
            node_institutions_url,
            payload,
            auth=write_contrib.auth)
        node.reload()
        assert res.status_code == 201
        assert write_contrib_institution in node.affiliated_institutions.all()

    def test_read_write_contributor_can_remove_affiliated_institution(
            self, app, write_contrib, write_contrib_institution, node, node_institutions_url):
        node.affiliated_institutions.add(write_contrib_institution)
        node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': write_contrib_institution._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url,
            payload,
            auth=write_contrib.auth)
        node.reload()
        assert res.status_code == 204
        assert write_contrib_institution not in node.affiliated_institutions.all()

    def test_contribs_cannot_perform_action(
            self, app, write_contrib, read_contrib,
            institution_one, read_contrib_institution,
            node, node_institutions_url):

        #   test_read_write_contributor_cannot_remove_admin_affiliated_institution
        node.affiliated_institutions.add(institution_one)
        node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': institution_one._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url,
            payload,
            auth=write_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert institution_one in node.affiliated_institutions.all()

    #   test_read_only_contributor_cannot_remove_admin_affiliated_institution
        node.affiliated_institutions.add(institution_one)
        node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': institution_one._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url,
            payload,
            auth=read_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert institution_one in node.affiliated_institutions.all()

    #   test_read_only_contributor_cannot_add_affiliated_institution
        payload = {
            'data': [{
                'type': 'institutions',
                'id': read_contrib_institution._id
            }]
        }
        res = app.post_json_api(
            node_institutions_url,
            payload,
            auth=read_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert read_contrib_institution not in node.affiliated_institutions.all()

    #   test_read_only_contributor_cannot_remove_affiliated_institution
        node.affiliated_institutions.add(read_contrib_institution)
        node.save()
        payload = {
            'data': [{
                'type': 'institutions',
                'id': read_contrib_institution._id
            }]
        }
        res = app.delete_json_api(
            node_institutions_url,
            payload,
            auth=read_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert read_contrib_institution in node.affiliated_institutions.all()
