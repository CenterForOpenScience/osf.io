import pytest

from framework.auth import Auth
from osf.models import NodeLog
from api.logs.serializers import NodeLogSerializer
from osf_tests.factories import ProjectFactory, UserFactory
from tests.utils import make_drf_request_with_version

pytestmark = pytest.mark.django_db

class TestNodeLogSerializer:

    # Regression test for https://openscience.atlassian.net/browse/PLAT-758
    def test_serializing_log_with_legacy_non_registered_contributor_data(self, fake):
        # Old logs store unregistered contributors in params as dictionaries of the form:
        # {
        #     'nr_email': <email>,
        #     'nr_name': <name>,
        # }
        # This test ensures that the NodeLogSerializer can handle this legacy data.
        project = ProjectFactory()
        user = UserFactory()
        request = make_drf_request_with_version()
        nr_data = {'nr_email': fake.email(), 'nr_name': fake.name()}
        log = project.add_log(
            action=NodeLog.CONTRIB_ADDED,
            auth=Auth(project.creator),
            params={
                'project': project._id,
                'node': project._id,
                'contributors': [user._id, nr_data],
            }
        )
        serialized = NodeLogSerializer(log, context={'request': request}).data
        contributor_data = serialized['data']['attributes']['params']['contributors']
        # contributor_data will have two dicts:
        # the first will be the registered contrib, 2nd will be non-reg contrib
        reg_contributor_data, unreg_contributor_data = contributor_data
        assert reg_contributor_data['id'] == user._id
        assert reg_contributor_data['full_name'] == user.fullname

        assert unreg_contributor_data['id'] is None
        assert unreg_contributor_data['full_name'] == nr_data['nr_name']
