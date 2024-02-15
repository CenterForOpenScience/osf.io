import pytest
import responses

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
from addons.dataverse.tests.factories import DataverseAccountFactory
from api_tests.draft_nodes.views.test_draft_node_files_lists import prepare_mock_wb_response
from addons.dataverse.models import DataverseFile


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeFileList:

    @pytest.fixture()
    def dataverse(self, user, node):
        addon = node.add_addon('dataverse', auth=Auth(user))
        oauth_settings = DataverseAccountFactory()
        oauth_settings.save()
        user.add_addon('dataverse')
        user.external_accounts.add(oauth_settings)
        user.save()
        addon.user_settings = user.get_addon('dataverse')
        addon.external_account = oauth_settings
        addon.dataset_doi = 'test dataset_doi'
        addon.dataset = 'test dataset'
        addon._dataset_id = 'test dataset_id'
        addon.save()
        addon.user_settings.oauth_grants[node._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()
        node.save()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_one')

    @pytest.fixture()
    def dataverse_published_filenode(self, node):
        return DataverseFile.objects.create(
            target=node,
            path='/testpath',
            _history=[{'extra': {'datasetVersion': 'latest-published'}}],
        )

    @pytest.fixture()
    def dataverse_draft_filenode(self, node):
        return DataverseFile.objects.create(
            target=node,
            path='/testpath',
            _history=[{'extra': {'datasetVersion': 'latest'}}],
        )

    @pytest.fixture()
    def deleted_file(self, user, node):
        deleted_file = api_utils.create_test_file(
            node, user, filename='file_two')
        deleted_file.delete(user=user, save=True)
        return deleted_file

    def test_does_not_return_trashed_files(
            self, app, user, node, file, deleted_file):
        res = app.get(
            f'/{API_BASE}nodes/{node._id}/files/osfstorage/',
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 1

    @responses.activate
    def test_disambiguate_dataverse_paths_initial(self, app, user, node, dataverse):
        '''
        This test is for retrieving files from Dataverse initially, (Osf is contacting Dataverse after a update to their
        Dataverse files) this test ensures both files are made into OSF filenodes and their `extra` info is passed along
        to the front-end.
        '''
        prepare_mock_wb_response(
            path='/',
            node=node,
            provider='dataverse',
            files=[
                {
                    'name': 'testpath',
                    'path': '/testpath',
                    'materialized': '/testpath',
                    'kind': 'file',
                    'modified': 'Wed, 20 Jul 2011 22:04:50 +0000',
                    'extra': {
                        'datasetVersion': 'latest'
                    },
                    'provider': 'dataverse'
                },
                {
                    'name': 'testpath',
                    'path': '/testpath',
                    'materialized': '/testpath',
                    'kind': 'file',
                    'modified': 'Wed, 20 Jul 2011 22:04:50 +0000',
                    'extra': {
                        'datasetVersion': 'latest-published'
                    },
                    'provider': 'dataverse'
                },
            ]
        )
        res = app.get(
            f'/{API_BASE}nodes/{node._id}/files/dataverse/?sort=date_modified',
            auth=node.creator.auth
        )
        data = res.json['data']
        assert len(data) == 2
        dataset_versions = {
            _datum['attributes']['extra']['datasetVersion']
            for _datum in data
        }
        assert dataset_versions == {'latest', 'latest-published'}

    @responses.activate
    def test_disambiguate_dataverse_paths_retrieve(self, app, user, node, dataverse, dataverse_draft_filenode, dataverse_published_filenode):
        '''
        This test is for retrieving files from Dataverse and disambiguating their corresponding OSF filenodes and
        ensures their `extra` info is passed along to the front-end. Waterbulter must also be mocked here, otherwise OSF
        will assume the files are gone.
        '''
        prepare_mock_wb_response(
            path='/',
            node=node,
            provider='dataverse',
            files=[
                {
                    'name': 'testpath',
                    'path': '/testpath',
                    'materialized': '/testpath',
                    'kind': 'file',
                    'extra': {
                        'datasetVersion': 'latest',
                    },
                    'provider': 'dataverse',
                },
                {
                    'name': 'testpath',
                    'path': '/testpath',
                    'materialized': '/testpath',
                    'kind': 'file',
                    'extra': {
                        'datasetVersion': 'latest-published',
                    },
                    'provider': 'dataverse',
                },
            ]
        )
        res = app.get(
            f'/{API_BASE}nodes/{node._id}/files/dataverse/?sort=date_modified',
            auth=node.creator.auth
        )
        data = res.json['data']
        assert len(data) == 2
        dataset_versions = {
            _datum['attributes']['extra']['datasetVersion']
            for _datum in data
        }
        assert dataset_versions == {'latest', 'latest-published'}


@pytest.mark.django_db
class TestFileFiltering:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file_one(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_one')

    @pytest.fixture()
    def file_two(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_two')

    @pytest.fixture()
    def file_three(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_three')

    @pytest.fixture()
    def file_four(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_four')

    def test_get_all_files(
            self, app, user, node, file_one, file_two,
            file_three, file_four
    ):
        res = app.get(
            f'/{API_BASE}nodes/{node._id}/files/osfstorage/',
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 4

    def test_filter_on_single_tag(
            self, app, user, node,
            file_one, file_two,
            file_three, file_four
    ):
        file_one.add_tag('new', Auth(user))
        file_two.add_tag('new', Auth(user))
        file_three.add_tag('news', Auth(user))

        # test_filter_on_tag
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 2
        names = [f['attributes']['name'] for f in data]
        assert 'file_one' in names
        assert 'file_two' in names

        # test_filtering_tags_exact
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=news'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

        # test_filtering_tags_capitalized_query
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=NEWS'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

        # test_filtering_tags_capitalized_tag
        file_four.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_on_multiple_tags(
            self, app, user, node, file_one
    ):
        # test_filtering_on_multiple_tags_one_match
        file_one.add_tag('cat', Auth(user))

        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id), auth=user.auth)
        assert len(res.json.get('data')) == 0

        # test_filtering_on_multiple_tags_both_match
        file_one.add_tag('sand', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id), auth=user.auth)
        assert len(res.json.get('data')) == 1

    def test_filtering_by_tags_returns_distinct(
            self, app, user, node, file_one
    ):
        # regression test for returning multiple of the same file
        file_one.add_tag('cat', Auth(user))
        file_one.add_tag('cAt', Auth(user))
        file_one.add_tag('caT', Auth(user))
        file_one.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1
