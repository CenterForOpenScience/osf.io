import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
    NodeFactory,
)
from osf.utils import permissions


@pytest.mark.django_db
class RelationshipInstitutionsTestMixin:

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
    def resource_url(self, node):
        return f'/{API_BASE}nodes/{node._id}/relationships/institutions/'

    @pytest.fixture()
    def user(self, institution_one, institution_two):
        user_auth = AuthUserFactory()
        user_auth.add_or_update_affiliated_institution(institution_one)
        user_auth.add_or_update_affiliated_institution(institution_two)
        user_auth.save()
        return user_auth

    @pytest.fixture()
    def write_contrib(self, write_contrib_institution):
        user_auth = AuthUserFactory()
        user_auth.add_or_update_affiliated_institution(write_contrib_institution)
        user_auth.save()
        return user_auth

    @pytest.fixture()
    def read_contrib(self, read_contrib_institution):
        user_auth = AuthUserFactory()
        user_auth.add_or_update_affiliated_institution(read_contrib_institution)
        user_auth.save()
        return user_auth

    @pytest.fixture()
    def unauthorized_user_with_affiliation(self, read_contrib_institution):
        unauthorized_user = AuthUserFactory()
        unauthorized_user.add_or_update_affiliated_institution(read_contrib_institution)
        unauthorized_user.save()
        return unauthorized_user

    @pytest.fixture()
    def affiliated_admin(self, node, institution_one):
        admin = AuthUserFactory()
        admin.add_or_update_affiliated_institution(institution_one)
        admin.save()
        node.add_contributor(
            admin,
            permissions=permissions.ADMIN
        )

        return admin

    @pytest.fixture()
    def unauthorized_user_without_affiliation(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user, write_contrib, read_contrib):
        project = NodeFactory(creator=user)
        project.add_contributor(
            write_contrib,
            permissions=permissions.WRITE
        )
        project.add_contributor(
            read_contrib,
            permissions=permissions.READ
        )
        project.save()
        return project

    @pytest.fixture()
    def public_node(self, user):
        return NodeFactory(
            creator=user,
            is_public=True,
        )

    @pytest.fixture()
    def node_institutions_url(self, node):
        return f'/{API_BASE}nodes/{node._id}/relationships/institutions/'

    @pytest.fixture()
    def public_node_institutions_url(self, public_node):
        return f'/{API_BASE}nodes/{public_node._id}/relationships/institutions/'

    def create_payload(self, institutions):
        return {
            'data': [
                {'type': 'institutions', 'id': institution._id} for institution in institutions
            ]
        }

@pytest.mark.usefixtures('mock_send_grid')
@pytest.mark.usefixtures('mock_notification_send')
class TestNodeRelationshipInstitutions(RelationshipInstitutionsTestMixin):

    def test_node_with_no_permissions(self, app, unauthorized_user_with_affiliation, institution_one, node_institutions_url):
        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=unauthorized_user_with_affiliation.auth,
            expect_errors=True,
        )
        assert res.status_code == 403

    def test_user_with_no_institution(self, app, unauthorized_user_without_affiliation, institution_one, node_institutions_url):
        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            expect_errors=True,
            auth=unauthorized_user_without_affiliation.auth
        )
        assert res.status_code == 403

    def test_institution_does_not_exist(self, app, user, institution_one, node_institutions_url):
        res = app.put_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': '∆'
                    }
                ]
            },
            expect_errors=True,
            auth=user.auth
        )
        assert res.status_code == 404

    def test_wrong_type(self, app, user, institution_one, node_institutions_url):
        res = app.put_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'not_institution', 'id': institution_one._id
                    }
                ]
            },
            expect_errors=True,
            auth=user.auth
        )
        assert res.status_code == 409

    def test_remove_institutions_with_no_permissions(self, app, user, institution_one, node_institutions_url):
        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([]),
            expect_errors=True
        )
        assert res.status_code == 401

    def test_retrieve_private_node_no_auth(self, app, user, institution_one, node_institutions_url):
        res = app.get(node_institutions_url, expect_errors=True)
        assert res.status_code == 401

    def test_get_public_node(self, app, node, public_node_institutions_url):
        res = app.get(public_node_institutions_url)
        assert res.status_code == 200
        assert res.json['data'] == []

    def test_user_with_institution_and_permissions(
            self, app, user, institution_one, institution_two, node, node_institutions_url):
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.post_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth
        )

        assert res.status_code == 201
        data = res.json['data']
        ret_institutions = [inst['id'] for inst in data]

        assert institution_one._id in ret_institutions
        assert institution_two._id in ret_institutions
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_user_with_institution_and_permissions_through_patch(self, app, user, institution_one, institution_two,
                                                                 node, node_institutions_url, mock_notification_send):

        mock_notification_send.reset_mock()
        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth
        )
        assert res.status_code == 200
        assert mock_notification_send.call_count == 2

        first_call_args = mock_notification_send.call_args_list[0][1]
        assert first_call_args['to_addr'] == user.email
        assert first_call_args['subject'] == 'Project Affiliation Changed'

        second_call_args = mock_notification_send.call_args_list[1][1]
        assert second_call_args['to_addr'] == user.email
        assert second_call_args['subject'] == 'Project Affiliation Changed'

    def test_remove_institutions_with_affiliated_user(self, app, user, institution_one, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        mock_notification_send.reset_mock()
        res = app.put_json_api(
            node_institutions_url,
            {
                'data': []
            },
            auth=user.auth
        )

        first_call_args = mock_notification_send.call_args_list[0][1]
        assert first_call_args['to_addr'] == user.email
        assert first_call_args['subject'] == 'Project Affiliation Changed'

        assert res.status_code == 200
        assert node.affiliated_institutions.count() == 0

    def test_using_post_making_no_changes_returns_201(self, app, user, institution_one, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()

        mock_notification_send.reset_mock()
        res = app.post_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user.auth
        )
        mock_notification_send.assert_not_called()

        assert res.status_code == 201
        assert institution_one in node.affiliated_institutions.all()

    def test_put_not_admin_but_affiliated(self, app, institution_one, node, node_institutions_url):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution_one)
        user.save()
        node.add_contributor(user)
        node.save()

        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user.auth
        )

        assert res.status_code == 200
        assert institution_one in node.affiliated_institutions.all()

    def test_add_through_patch_one_inst_to_node_with_inst(
            self, app, user, institution_one, institution_two, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        mock_notification_send.reset_mock()
        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth
        )
        assert mock_notification_send.call_count == 1
        first_call_args = mock_notification_send.call_args_list[0][1]
        assert first_call_args['to_addr'] == user.email
        assert first_call_args['subject'] == 'Project Affiliation Changed'

        assert res.status_code == 200
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_add_through_patch_one_inst_while_removing_other(
            self, app, user, institution_one, institution_two, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        mock_notification_send.reset_mock()
        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_two]),
            auth=user.auth
        )
        assert mock_notification_send.call_count == 2

        first_call_args = mock_notification_send.call_args_list[0][1]
        assert first_call_args['to_addr'] == user.email
        assert first_call_args['subject'] == 'Project Affiliation Changed'

        second_call_args = mock_notification_send.call_args_list[1][1]
        assert second_call_args['to_addr'] == user.email
        assert second_call_args['subject'] == 'Project Affiliation Changed'

        assert res.status_code == 200
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_add_one_inst_with_post_to_node_with_inst(
            self, app, user, institution_one, institution_two, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.post_json_api(
            node_institutions_url,
            self.create_payload([institution_two]),
            auth=user.auth
        )
        call_args = mock_notification_send.call_args[1]
        assert call_args['to_addr'] == user.email
        assert call_args['subject'] == 'Project Affiliation Changed'

        assert res.status_code == 201
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_delete_nothing(self, app, user, node_institutions_url):
        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([]),
            auth=user.auth
        )
        assert res.status_code == 204

    def test_delete_existing_inst(self, app, user, institution_one, node, node_institutions_url, mock_notification_send):
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user.auth
        )

        call_args = mock_notification_send.call_args[1]
        assert call_args['to_addr'] == user.email
        assert call_args['subject'] == 'Project Affiliation Changed'

        assert res.status_code == 204
        assert institution_one not in node.affiliated_institutions.all()

    def test_delete_not_affiliated_and_affiliated_insts(
            self, app, user, institution_one, institution_two, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth,
        )

        assert res.status_code == 204
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

    def test_delete_user_is_admin(self, app, user, institution_one, node, resource_url):
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            resource_url,
            self.create_payload([institution_one]),
            auth=user.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_read_write(self, app, affiliated_admin, institution_one, node, node_institutions_url):
        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=affiliated_admin.auth
        )

        assert res.status_code == 204

    def test_delete_user_is_read_only(self, app, institution_one, node, node_institutions_url):
        user_auth = AuthUserFactory()
        user_auth.add_or_update_affiliated_institution(institution_one)
        user_auth.save()
        node.add_contributor(user_auth, permissions=permissions.READ)
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user_auth.auth,
            expect_errors=True
        )

        assert res.status_code == 403

    def test_delete_user_is_admin_but_not_affiliated_with_inst(self, app, institution_one):
        user_auth = AuthUserFactory()
        project = NodeFactory(creator=user_auth)
        project.affiliated_institutions.add(institution_one)
        project.save()
        assert institution_one in project.affiliated_institutions.all()

        res = app.delete_json_api(
            f'/{API_BASE}nodes/{project._id}/relationships/institutions/',
            self.create_payload([institution_one]),
            auth=user_auth.auth,
        )

        assert res.status_code == 204
        assert institution_one not in project.affiliated_institutions.all()

    def test_admin_can_add_affiliated_institution(self, app, user, institution_one, node, node_institutions_url):
        res = app.post_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    }
                ]
            },
            auth=user.auth
        )
        assert res.status_code == 201
        assert institution_one in node.affiliated_institutions.all()

    def test_admin_can_remove_admin_affiliated_institution(
            self, app, user, institution_one, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    }
                ]
            },
            auth=user.auth
        )
        assert res.status_code == 204
        assert institution_one not in node.affiliated_institutions.all()

    def test_admin_can_remove_read_write_contributor_affiliated_institution(
            self, app, user, read_contrib_institution, node, node_institutions_url):
        node.affiliated_institutions.add(read_contrib_institution)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': read_contrib_institution._id
                    }
                ]
            },
            auth=user.auth
        )
        assert res.status_code == 204
        assert read_contrib_institution not in node.affiliated_institutions.all()

    def test_read_write_contributor_can_add_affiliated_institution(
            self, app, write_contrib, write_contrib_institution, node, node_institutions_url):
        res = app.post_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': write_contrib_institution._id
                    }
                ]
            },
            auth=write_contrib.auth
        )
        assert res.status_code == 201
        assert write_contrib_institution in node.affiliated_institutions.all()

    def test_read_write_contributor_can_remove_affiliated_institution(
            self, app, write_contrib, write_contrib_institution, node, node_institutions_url):
        node.affiliated_institutions.add(write_contrib_institution)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': write_contrib_institution._id
                    }
                ]
            },
            auth=write_contrib.auth)
        assert res.status_code == 204
        assert write_contrib_institution not in node.affiliated_institutions.all()

    def test_read_write_contributor_cannot_remove_admin_affiliated_institution(
            self, app, write_contrib, read_contrib,
            institution_one, read_contrib_institution,
            node, node_institutions_url):

        node.affiliated_institutions.add(institution_one)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    }
                ]
            },
            auth=write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert institution_one in node.affiliated_institutions.all()

    def test_read_only_contributor_cannot_remove_admin_affiliated_institution(
            self, app, write_contrib, read_contrib,
            institution_one, read_contrib_institution,
            node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    }
                ]
            },
            auth=read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert institution_one in node.affiliated_institutions.all()

    def test_read_only_contributor_cannot_add_affiliated_institution(
            self, app, write_contrib, read_contrib, institution_one, read_contrib_institution, node,
            node_institutions_url):

        res = app.post_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': read_contrib_institution._id
                    }
                ]
            },
            auth=read_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert read_contrib_institution not in node.affiliated_institutions.all()

    def test_read_only_contributor_cannot_remove_affiliated_institution(
            self, app, write_contrib, read_contrib,
            institution_one, read_contrib_institution,
            node, node_institutions_url):

        node.affiliated_institutions.add(read_contrib_institution)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            {
                'data': [
                    {
                        'type': 'institutions',
                        'id': read_contrib_institution._id
                    }
                ]
            },
            auth=read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert read_contrib_institution in node.affiliated_institutions.all()
