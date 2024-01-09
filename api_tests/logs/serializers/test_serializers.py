import mock
import pytest

from framework.auth import Auth
from osf.models import NodeLog
from api.logs.serializers import NodeLogSerializer, NodeLogDownloadSerializer, NodeLogDownloadParamsSerializer
from osf_tests.factories import ProjectFactory, UserFactory
from tests.base import assert_datetime_equal
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


class TestNodeLogDownloadSerializer:
    def get_test_context_embed_user(self, *args, **kwargs):
        return {
            'data': {
                'attributes': {
                    'full_name': 'test_user'
                }
            }
        }

    def test_serializing_log_with_legacy_non_registered_contributor_data(self, fake):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        nr_data = {'nr_email': fake.email(), 'nr_name': fake.name()}
        log = project.add_log(
            action=NodeLog.CONTRIB_ADDED,
            auth=Auth(project.creator),
            params={
                'project': project._id,
                'node': project._id,
                'contributors': [nr_data],
            }
        )
        serialized = NodeLogDownloadSerializer(log, context={'request': request}).data
        assert serialized['targetUserFullId'] is None
        assert serialized['targetUserFullName'] == nr_data['nr_name']

    def test_to_representation(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        log = project.add_log(
            action='osf_storage_folder_created',
            auth=Auth(project.creator),
            params={
                'node': project._id,
                'path': 'test_folder',
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
            },
        )

        serialized = NodeLogDownloadSerializer(
            log,
            context={'request': request, 'embed': {'user': self.get_test_context_embed_user}}
        ).data
        assert_datetime_equal(
            serialized['date'],
            project.logs.first().date
        )
        assert serialized['user'] == 'test_user'
        assert serialized['project_id'] == project._id
        assert serialized['project_title'] == project.title
        assert serialized['action'] == project.logs.first().action

    def test_to_representation__params_include_contributors(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        contrib = UserFactory()
        project.add_contributor(contrib, auth=Auth(project.creator))
        serialized = NodeLogDownloadSerializer(project.logs.latest(), context={'request': request}).data
        assert serialized['action'] == 'contributor_added'
        assert serialized['targetUserFullId'] == contrib._id
        assert serialized['targetUserFullName'] == contrib.fullname

    def test_to_representation__action_include_checked(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        log = project.add_log(
            'checked_out',
            auth=Auth(project.creator),
            params={
                'kind': 'file',
                'node': project._id,
                'path': 'test_file',
                'urls': {
                    'view': 'www.fake.org',
                    'download': 'www.fake.com',
                },
                'project': project._id
            }
        )
        serialized = NodeLogDownloadSerializer(log, context={'request': request}).data
        assert serialized['action'] == 'checked_out'
        assert serialized['item'] == 'file'
        assert serialized['path'] == 'test_file'

    def test_to_representation__action_include_osf_storage(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        log = project.add_log(
            'osf_storage_folder_created',
            auth=Auth(project.creator),
            params={
                'node': project._id,
                'path': 'test_folder',
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
            },
        )
        serialized = NodeLogDownloadSerializer(log, context={'request': request}).data
        assert serialized['action'] == 'osf_storage_folder_created'
        assert serialized['path'] == 'test_folder'

    def test_to_representation__action_include_addon(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        project.add_addon('github', auth=Auth(project.creator))
        serialized = NodeLogDownloadSerializer(project.logs.latest(), context={'request': request}).data
        assert serialized['action'] == 'addon_added'
        assert serialized['addon'] == 'GitHub'

    def test_to_representation__action_include_tag(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        project.add_tag('Rheisen', auth=Auth(project.creator))
        serialized = NodeLogDownloadSerializer(project.logs.latest(), context={'request': request}).data
        assert serialized['action'] == 'tag_added'
        assert serialized['tag'] == 'Rheisen'

    def test_to_representation__action_include_wiki(self):
        project = ProjectFactory()
        request = make_drf_request_with_version()
        log = project.add_log(
            'wiki_updated',
            auth=Auth(project.creator),
            params={
                'project': project.parent_id,
                'node': project._primary_key,
                'page': 'test',
                'page_id': 'test_id',
                'version': 1,
            }
        )
        serialized = NodeLogDownloadSerializer(log, context={'request': request}).data
        assert serialized['action'] == 'wiki_updated'
        assert serialized['version'] == '1'
        assert serialized['page'] == 'test'


class TestNodeLogDownloadParamsSerializer:
    def test_get_params_node(self):
        project = ProjectFactory()
        log = project.add_log(
            action=NodeLog.PROJECT_CREATED,
            auth=Auth(project.creator),
            params={
                'node': project._id,
            }
        )
        request = make_drf_request_with_version()
        serialized = NodeLogDownloadParamsSerializer(log.params, context={'request': request}).data
        assert serialized['params_node'] is not None
        assert serialized['params_node']['id'] == project._id
        assert serialized['params_node']['title'] == project.title

    def test_get_params_node__return_none(self):
        request = make_drf_request_with_version()
        serialized = NodeLogDownloadParamsSerializer({}, context={'request': request}).data
        assert serialized['params_node'] is None

    def test_get_contributors(self, fake):
        project = ProjectFactory()
        user = UserFactory()
        user.unclaimed_records = {
            project._id: {
                'name': 'test_unclaimed_records_name'
            }
        }
        user.save()
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
        serialized = NodeLogDownloadParamsSerializer(log.params, context={'request': request}).data
        # Assert the first contibutor
        assert serialized['contributors'][0]['id'] == user._id
        assert serialized['contributors'][0]['full_name'] == user.fullname
        assert serialized['contributors'][0]['unregistered_name'] == 'test_unclaimed_records_name'
        assert serialized['contributors'][0]['active'] is True
        # Assert the second contibutor
        assert serialized['contributors'][1]['id'] is None
        assert serialized['contributors'][1]['full_name'] == nr_data['nr_name']
        assert serialized['contributors'][1]['unregistered_name'] == nr_data['nr_name']
        assert serialized['contributors'][1]['active'] is False

    @mock.patch('api.logs.serializers.is_anonymized')
    def test_get_contributors__anonymized(self, mock_is_anonymized):
        mock_is_anonymized.return_value = True
        project = ProjectFactory()
        user = UserFactory()
        request = make_drf_request_with_version()
        log = project.add_log(
            action=NodeLog.CONTRIB_ADDED,
            auth=Auth(project.creator),
            params={
                'project': project._id,
                'node': project._id,
                'contributors': [user._id],
            }
        )
        serialized = NodeLogDownloadParamsSerializer(log.params, context={'request': request}).data
        assert mock_is_anonymized.called
        assert serialized['contributors'] == []
