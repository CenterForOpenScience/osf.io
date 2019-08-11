import pytest

from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_bibliographic_contributors_list import TestNodeBibliographicContributors
from osf_tests.factories import (
    RegistrationFactory,
    ProjectFactory
)
from osf.utils.permissions import READ, WRITE


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestRegistrationBibliographicContributors(TestNodeBibliographicContributors):

    @pytest.fixture()
    def project(self, admin_contributor_bib, write_contributor_non_bib, read_contributor_bib):
        project = ProjectFactory(creator=admin_contributor_bib)
        reg = RegistrationFactory(
            creator=admin_contributor_bib,
            project=project
        )
        reg.add_contributor(write_contributor_non_bib, WRITE, visible=False)
        reg.add_contributor(read_contributor_bib, READ)
        reg.save()
        return reg

    @pytest.fixture()
    def url(self, project):
        return '/{}registrations/{}/bibliographic_contributors/'.format(API_BASE, project._id)
