import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_relationship_institutions import RelationshipInstitutionsTestMixin
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
)
from osf.utils import permissions


@pytest.mark.django_db
class TestRegistrationRelationshipInstitutions(RelationshipInstitutionsTestMixin):

    @pytest.fixture()
    def node(self, user, write_contrib, read_contrib):
        # Overrides TestNodeRelationshipInstitutions
        registration = RegistrationFactory(creator=user)
        registration.add_contributor(
            write_contrib,
            permissions=permissions.WRITE,
            notification_type=False
        )
        registration.add_contributor(
            read_contrib,
            permissions=permissions.READ,
            notification_type=False
        )
        registration.save()
        return registration

    @pytest.fixture()
    def make_resource_url(self, resource):
        return f'/{API_BASE}registrations/{resource._id}/relationships/institutions/'

    @pytest.fixture()
    def node_institutions_url(self, node):
        return f'/{API_BASE}registrations/{node._id}/relationships/institutions/'

    @pytest.fixture()
    def resource_factory(self):
        # Overrides TestNodeRelationshipInstitutions
        return RegistrationFactory

    # test override, write contribs can't update institution
    def test_put_not_admin_but_affiliated_read_permission(self, app, institution_one, node, node_institutions_url):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution_one)
        user.save()
        node.add_contributor(user, permissions=permissions.READ)
        node.save()

        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            expect_errors=True,
            auth=user.auth
        )

        node.reload()
        assert res.status_code == 403
        assert institution_one not in node.affiliated_institutions.all()

    def test_put_not_admin_but_affiliated_and_write_permission(self, app, institution_one, node, node_institutions_url):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution_one)
        user.save()
        node.add_contributor(user)
        node.save()

        res = app.put_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            expect_errors=True,
            auth=user.auth
        )

        node.reload()
        assert res.status_code == 200
        assert institution_one in node.affiliated_institutions.all()

    # test override, write contribs can delete
    def test_delete_user_is_read_write(self, app, institution_one, node, node_institutions_url):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution_one)
        user.save()
        node.add_contributor(user)
        node.affiliated_institutions.add(institution_one)
        node.save()

        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 204

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
            auth=write_contrib.auth,
            expect_errors=True
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
            auth=write_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 204
        assert write_contrib_institution not in node.affiliated_institutions.all()

    def test_user_with_institution_and_permissions_through_patch(self, app, user, institution_one, institution_two,
                                                                 node, node_institutions_url):
        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth
        )
        assert res.status_code == 200

    def test_delete_existing_inst(self, app, user, institution_one, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        res = app.delete_json_api(
            node_institutions_url,
            self.create_payload([institution_one]),
            auth=user.auth
        )
        assert res.status_code == 204
        assert institution_one not in node.affiliated_institutions.all()

    def test_remove_institutions_with_affiliated_user(self, app, user, institution_one, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        res = app.put_json_api(
            node_institutions_url,
            {
                'data': []
            },
            auth=user.auth
        )

        assert res.status_code == 200
        assert node.affiliated_institutions.count() == 0

    def test_add_through_patch_one_inst_to_node_with_inst(
            self, app, user, institution_one, institution_two, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_one, institution_two]),
            auth=user.auth
        )

        assert res.status_code == 200
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()

    def test_add_through_patch_one_inst_while_removing_other(
            self, app, user, institution_one, institution_two, node, node_institutions_url):
        node.affiliated_institutions.add(institution_one)
        node.save()
        assert institution_one in node.affiliated_institutions.all()
        assert institution_two not in node.affiliated_institutions.all()

        res = app.patch_json_api(
            node_institutions_url,
            self.create_payload([institution_two]),
            auth=user.auth
        )

        assert res.status_code == 200
        assert institution_one not in node.affiliated_institutions.all()
        assert institution_two in node.affiliated_institutions.all()
