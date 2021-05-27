import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_relationship_institutions import TestNodeRelationshipInstitutions
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
)
from osf.utils import permissions


@pytest.mark.django_db
class TestRegistrationRelationshipInstitutions(TestNodeRelationshipInstitutions):

    @pytest.fixture()
    def node(self, user, write_contrib, read_contrib):
        # Overrides TestNodeRelationshipInstitutions
        registration = RegistrationFactory(creator=user)
        registration.add_contributor(
            write_contrib,
            permissions=permissions.WRITE)
        registration.add_contributor(read_contrib, permissions=permissions.READ)
        registration.save()
        return registration

    @pytest.fixture()
    def make_resource_url(self):
        # Overrides TestNodeRelationshipInstitutions
        def make_resource_url(resource):
            return '/{}registrations/{}/relationships/institutions/'.format(
                API_BASE, resource._id)
        return make_resource_url

    @pytest.fixture()
    def node_institutions_url(self, node):
        # Overrides TestNodeRelationshipInstitutions
        return '/{0}registrations/{1}/relationships/institutions/'.format(
            API_BASE, node._id)

    @pytest.fixture()
    def resource_factory(self):
        # Overrides TestNodeRelationshipInstitutions
        return RegistrationFactory

    # test override, write contribs can't update institution
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
            expect_errors=True,
            auth=user.auth
        )

        node.reload()
        assert res.status_code == 403
        assert institution_one not in node.affiliated_institutions.all()

    # test override, write contribs cannot delete
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
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403

    # test override, write contribs cannot add institution
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
            auth=write_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert write_contrib_institution not in node.affiliated_institutions.all()

    # test override, write contribs cannot delete
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
            auth=write_contrib.auth,
            expect_errors=True)
        node.reload()
        assert res.status_code == 403
        assert write_contrib_institution in node.affiliated_institutions.all()
