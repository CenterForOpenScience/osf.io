import pytest

from osf.utils.workflows import DefaultStates, RequestTypes
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    NodeRequestFactory
)
from osf.utils import permissions

@pytest.mark.django_db
class NodeRequestTestMixin(object):

    @pytest.fixture()
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def requester(self):
        return AuthUserFactory()

    @pytest.fixture()
    def noncontrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, admin, write_contrib):
        proj = ProjectFactory(creator=admin)
        proj.save()
        proj.add_contributor(
            contributor=write_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            send_email='access_request',
            save=True
        )
        return proj

    @pytest.fixture()
    def node_request(self, project, requester):
        node_request = NodeRequestFactory(
            creator=requester,
            target=project,
            request_type=RequestTypes.ACCESS.value,
            machine_state=DefaultStates.INITIAL.value
        )
        node_request.run_submit(requester)
        return node_request

    @pytest.fixture()
    def second_admin(self, project):
        second_admin = AuthUserFactory()
        project.add_contributor(
            contributor=second_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True
        )
        return second_admin
