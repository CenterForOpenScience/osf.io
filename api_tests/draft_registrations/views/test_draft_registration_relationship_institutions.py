import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_relationship_institutions import TestNodeRelationshipInstitutions

from osf_tests.factories import DraftRegistrationFactory
from osf.utils import permissions


@pytest.mark.django_db
class TestDraftRegistrationRelationshipInstitutions(TestNodeRelationshipInstitutions):
    @pytest.fixture()
    def resource_factory(self):
        # Overrides TestNodeRelationshipInstitutions
        return DraftRegistrationFactory

    @pytest.fixture()
    def node(self, user, write_contrib, read_contrib):
        # Overrides TestNodeRelationshipInstitutions
        draft = DraftRegistrationFactory(initiator=user)
        draft.add_contributor(
            write_contrib,
            permissions=permissions.WRITE)
        draft.add_contributor(read_contrib, permissions=permissions.READ)
        draft.save()
        return draft

    @pytest.fixture()
    def make_resource_url(self):
        # Overrides TestNodeRelationshipInstitutions
        def make_resource_url(resource):
            return '/{}draft_registrations/{}/relationships/institutions/'.format(
                API_BASE, resource._id)
        return make_resource_url

    @pytest.fixture()
    def node_institutions_url(self, node):
        # Overrides TestNodeRelationshipInstitutions
        return '/{0}draft_registrations/{1}/relationships/institutions/'.format(
            API_BASE, node._id)

    # Overrides TestNodeRelationshipInstitutions
    def test_get_public_node(self, app, node, node_institutions_url):
        # Can't make draft registrations public
        return
