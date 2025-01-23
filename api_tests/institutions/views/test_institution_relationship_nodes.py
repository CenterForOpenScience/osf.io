import pytest
from unittest import mock

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    RegistrationFactory,
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from osf.utils import permissions


def make_payload(*node_ids):
    data = [
        {'type': 'nodes', 'id': id_} for id_ in node_ids
    ]
    return {'data': data}


def make_registration_payload(*node_ids):
    data = [
        {'type': 'registrations', 'id': id_} for id_ in node_ids
    ]
    return {'data': data}


@pytest.mark.django_db
class TestInstitutionRelationshipNodes:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def node(self):
        return NodeFactory()

    @pytest.fixture()
    def user(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.save()
        return user

    @pytest.fixture()
    def node_one(self, user, institution):
        node = NodeFactory(creator=user)
        node.affiliated_institutions.add(institution)
        node.save()
        return node

    @pytest.fixture()
    def node_without_institution(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def node_public(self, user, institution):
        node_public = NodeFactory(is_public=True)
        node_public.affiliated_institutions.add(institution)
        node_public.save()
        return node_public

    @pytest.fixture()
    def admin(self, institution, node_public):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        node_public.add_contributor(user, permissions=permissions.ADMIN)
        user.save()
        return user

    @pytest.fixture()
    def node_private(self, user, institution):
        node_private = NodeFactory()
        node_private.affiliated_institutions.add(institution)
        node_private.save()
        return node_private

    @pytest.fixture()
    def url_institution_nodes(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/relationships/nodes/'

    def test_get_nodes_no_auth(self, app, user, node_one, node_public, node_private, url_institution_nodes):

        res = app.get(url_institution_nodes)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_one._id not in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

    def test_get_nodes_with_auth(self, app, user, node_one, node_public, node_private, url_institution_nodes):

        res = app.get(url_institution_nodes, auth=user.auth)

        assert res.status_code == 200
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_one._id in node_ids
        assert node_public._id in node_ids
        assert node_private._id not in node_ids

    def test_node_does_not_exist(self, app, user, node_without_institution, url_institution_nodes):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload('notIdatAll'),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 404

    def test_node_type_does_not_exist(self, app, user, node_without_institution, url_institution_nodes):

        # test_node_type_does_not_exist
        res = app.post_json_api(
            url_institution_nodes,
            {'data': [{'type': 'dugtrio', 'id': node_without_institution._id}]},
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 409

    def test_user_with_nodes_and_permissions(
            self, user, app, node_without_institution,
            url_institution_nodes, institution
    ):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_without_institution._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node_ids = [node_['id'] for node_ in res.json['data']]
        assert node_without_institution._id in node_ids

        node_without_institution.reload()
        assert institution in node_without_institution.affiliated_institutions.all()

    def test_user_does_not_have_node(
            self, app, node,
            url_institution_nodes, user,
            institution
    ):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin(
            self, app, node_without_institution,
            url_institution_nodes, user,
            institution
    ):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_without_institution._id),
            auth=user.auth
        )
        assert res.status_code == 201
        node_without_institution.reload()
        assert institution in node_without_institution.affiliated_institutions.all()

    def test_user_is_read_write(
            self, app, node,
            url_institution_nodes,
            institution
    ):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
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

    def test_user_is_read_only(
            self, app, node,
            url_institution_nodes,
            institution
    ):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        node.add_contributor(user, permissions=permissions.READ)
        node.save()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            auth=user.auth, expect_errors=True
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_user_is_admin_but_not_affiliated(
            self, app, url_institution_nodes, institution):
        user = AuthUserFactory()
        node = NodeFactory(creator=user)
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 403
        node.reload()
        assert institution not in node.affiliated_institutions.all()

    def test_add_some_with_permissions_others_without(
            self, user, node, node_without_institution, app, url_institution_nodes, institution):
        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_without_institution._id, node._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 403
        node_without_institution.reload()
        node.reload()
        assert institution not in node_without_institution.affiliated_institutions.all()
        assert institution not in node.affiliated_institutions.all()

    def test_add_some_existant_others_not(
            self, institution, node_one, user,
            node_without_institution, app, url_institution_nodes
    ):
        assert institution in node_one.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_without_institution._id, node_one._id),
            auth=user.auth
        )

        assert res.status_code == 201
        node_one.reload()
        node_without_institution.reload()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_without_institution.affiliated_institutions.all()

    def test_only_add_existent_with_mixed_permissions(
            self, institution, node_one, node_public,
            app, url_institution_nodes, user
    ):
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_public._id, node_one._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 403
        node_one.reload()
        node_public.reload()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_public.affiliated_institutions.all()

    def test_only_add_existent_with_permissions(
            self, user, node_one, node_without_institution,
            institution, app,
            url_institution_nodes
    ):
        node_without_institution.affiliated_institutions.add(institution)
        node_without_institution.save()
        assert institution in node_one.affiliated_institutions.all()
        assert institution in node_without_institution.affiliated_institutions.all()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(node_without_institution._id, node_one._id),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_admin(
            self, app, url_institution_nodes,
            node_one, user, institution
    ):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id),
            auth=user.auth
        )
        node_one.reload()
        assert res.status_code == 204
        assert institution not in node_one.affiliated_institutions.all()

    def test_delete_user_is_read_write(
            self, app, node_private,
            user, url_institution_nodes,
            institution
    ):
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

    def test_delete_user_is_read_only(
            self, node_private, user,
            app, url_institution_nodes,
            institution):
        node_private.add_contributor(user, permissions=permissions.READ)
        node_private.save()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_private._id),
            auth=user.auth, expect_errors=True
        )
        node_private.reload()

        assert res.status_code == 403
        assert institution in node_private.affiliated_institutions.all()

    def test_delete_user_is_admin_and_affiliated_with_inst(
            self, institution, node_one, app, url_institution_nodes, user):
        assert institution in node_one.affiliated_institutions.all()

        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id),
            auth=user.auth
        )

        assert res.status_code == 204
        node_one.reload()
        assert institution not in node_one.affiliated_institutions.all()

    def test_delete_user_is_admin_but_not_affiliated_with_inst(
            self, institution, app, url_institution_nodes):
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

    def test_delete_user_is_affiliated_with_inst_and_mixed_permissions_on_nodes(
            self, app, url_institution_nodes, node_one, node_public, user):
        res = app.delete_json_api(
            url_institution_nodes,
            make_payload(node_one._id, node_public._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 403

    def test_add_non_node(self, app, user, institution, url_institution_nodes):
        registration = RegistrationFactory(creator=user, is_public=True)
        registration.affiliated_institutions.add(institution)
        registration.save()

        res = app.post_json_api(
            url_institution_nodes,
            make_payload(registration._id),
            expect_errors=True, auth=user.auth
        )

        assert res.status_code == 404

    def test_email_sent_on_affiliation_addition(self, app, user, institution, node_without_institution,
                                                url_institution_nodes):
        node_without_institution.add_contributor(user, permissions='admin')
        current_institution = InstitutionFactory()
        node_without_institution.affiliated_institutions.add(current_institution)

        with mock.patch('osf.models.mixins.mails.send_mail') as mocked_send_mail:
            res = app.post_json_api(
                url_institution_nodes,
                {
                    'data': [
                        {
                            'type': 'nodes', 'id': node_without_institution._id
                        }
                    ]
                },
                auth=user.auth
            )

            assert res.status_code == 201
            mocked_send_mail.assert_called_once()
            call_args = mocked_send_mail.call_args[1]
            assert institution in call_args['institution_added']
            assert set([current_institution, institution]) == set(call_args['current_affiliations'])

    def test_email_sent_on_affiliation_removal(self, app, admin, institution, node_public, url_institution_nodes):
        current_institution = InstitutionFactory()
        node_public.affiliated_institutions.add(current_institution)

        with mock.patch('osf.models.mixins.mails.send_mail') as mocked_send_mail:
            res = app.delete_json_api(
                url_institution_nodes,
                {
                    'data': [
                        {
                            'type': 'nodes', 'id': node_public._id
                        }
                    ]
                },
                auth=admin.auth
            )

            # Assert response is successful
            assert res.status_code == 204

            call_args = mocked_send_mail.call_args[1]
            assert call_args['current_affiliations'] == [current_institution]
            assert call_args['institution_removed'] == [institution]
            assert call_args['user'] == admin
            assert node_public == call_args['node']
