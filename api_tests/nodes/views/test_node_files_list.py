import datetime
import json

import furl
import responses
from django.utils import timezone
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from addons.github.models import GithubFolder
from addons.github.tests.factories import GitHubAccountFactory
from api.base.settings.defaults import API_BASE
from api.base.utils import waterbutler_api_url_for
from api_tests import utils as api_utils
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PrivateLinkFactory
)


def prepare_mock_wb_response(
        node=None,
        provider='github',
        files=None,
        folder=True,
        path='/',
        method=responses.GET,
        status_code=200
    ):
    """Prepare a mock Waterbutler response with responses library.

    :param Node node: Target node.
    :param str provider: Addon provider
    :param list files: Optional list of files. You can specify partial data; missing values
        will have defaults.
    :param folder: True if mocking out a folder response, False if a file response.
    :param path: Waterbutler path, passed to waterbutler_api_url_for.
    :param str method: HTTP method.
    :param int status_code: HTTP status.
    """
    node = node
    files = files or []
    wb_url = waterbutler_api_url_for(node._id, provider=provider, _internal=True, path=path, meta=True, view_only=None)

    default_file = {
        u'contentType': None,
        u'extra': {u'downloads': 0, u'version': 1},
        u'kind': u'file',
        u'modified': None,
        u'name': u'NewFile',
        u'path': u'/NewFile',
        u'provider': provider,
        u'size': None,
        u'materialized': '/',
    }

    if len(files):
        data = [dict(default_file, **each) for each in files]
    else:
        data = [default_file]

    jsonapi_data = []
    for datum in data:
        jsonapi_data.append({'attributes': datum})

    if not folder:
        jsonapi_data = jsonapi_data[0]

    responses.add(
        responses.Response(
            method,
            wb_url,
            json={u'data': jsonapi_data},
            status=status_code,
            content_type='application/json'
        )
    )


class TestNodeFilesList(ApiTestCase):

    def setUp(self):
        super(TestNodeFilesList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.private_url = '/{}nodes/{}/files/'.format(
            API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_url = '/{}nodes/{}/files/'.format(API_BASE, self.public_project._id)

    def add_github(self):
        user_auth = Auth(self.user)
        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.add_addon('github')
        self.user.external_accounts.add(oauth_settings)
        self.user.save()
        addon.user_settings = self.user.get_addon('github')
        addon.external_account = oauth_settings
        addon.save()
        self.project.save()
        addon.user_settings.oauth_grants[self.project._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()

    def view_only_link(self):
        private_link = PrivateLinkFactory(creator=self.user)
        private_link.nodes.add(self.project)
        private_link.save()
        return private_link

    def _prepare_mock_wb_response(self, node=None, **kwargs):
        prepare_mock_wb_response(node=node or self.project, **kwargs)

    def test_returns_public_files_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data'][0]['attributes']['provider'],
            'osfstorage'
        )
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_returns_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(
            res.json['data'][0]['attributes']['provider'],
            'osfstorage'
        )

    def test_returns_storage_addons_link(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_in('storage_addons', res.json['data'][0]['links'])

    def test_returns_file_data(self):
        fobj = self.project.get_addon(
            'osfstorage').get_root().append_file('NewFile')
        fobj.save()
        res = self.app.get(
            '{}osfstorage/{}'.format(self.private_url, fobj._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_true(isinstance(res.json['data'], dict))
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['kind'], 'file')
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')

    def test_returns_osfstorage_folder_version_two(self):
        fobj = self.project.get_addon(
            'osfstorage').get_root().append_folder('NewFolder')
        fobj.save()
        res = self.app.get(
            '{}osfstorage/'.format(self.private_url), auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_returns_osf_storage_folder_version_two_point_two(self):
        fobj = self.project.get_addon(
            'osfstorage').get_root().append_folder('NewFolder')
        fobj.save()
        res = self.app.get(
            '{}osfstorage/?version=2.2'.format(self.private_url), auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_list_returns_folder_data(self):
        fobj = self.project.get_addon(
            'osfstorage').get_root().append_folder('NewFolder')
        fobj.save()
        res = self.app.get(
            '{}osfstorage/'.format(self.private_url, fobj._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFolder')

    def test_returns_folder_data(self):
        fobj = self.project.get_addon(
            'osfstorage').get_root().append_folder('NewFolder')
        fobj.save()
        res = self.app.get(
            '{}osfstorage/{}/'.format(self.private_url, fobj._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 0)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_returns_private_files_logged_out(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_in('detail', res.json['errors'][0])

    def test_returns_private_files_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(len(res.json['data']), 1)
        assert_equal(
            res.json['data'][0]['attributes']['provider'],
            'osfstorage'
        )

    def test_returns_private_files_logged_in_non_contributor(self):
        res = self.app.get(
            self.private_url,
            auth=self.user_two.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_returns_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(
            res.json['data'][0]['attributes']['provider'],
            'osfstorage'
        )

        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.add_addon('github')
        self.user.external_accounts.add(oauth_settings)
        self.user.save()
        addon.user_settings = self.user.get_addon('github')
        addon.external_account = oauth_settings
        addon.save()
        self.project.save()
        addon.user_settings.oauth_grants[self.project._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()
        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        providers = [item['attributes']['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)

    @responses.activate
    def test_vol_node_files_list(self):
        self._prepare_mock_wb_response(
            provider='github', files=[{'name': 'NewFile'}])
        self.add_github()
        vol = self.view_only_link()
        url = '/{}nodes/{}/files/github/?view_only={}'.format(
            API_BASE, self.project._id, vol.key)
        res = self.app.get(url, auth=self.user_two.auth)
        wb_request = responses.calls[-1].request
        url = furl.furl(wb_request.url)

        assert_equal(url.query, 'meta=True&view_only={}'.format(unicode(vol.key, 'utf-8')))
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')
        assert_in(vol.key, res.json['data'][0]['links']['info'])
        assert_in(vol.key, res.json['data'][0]['links']['move'])
        assert_in(vol.key, res.json['data'][0]['links']['upload'])
        assert_in(vol.key, res.json['data'][0]['links']['download'])
        assert_in(vol.key, res.json['data'][0]['links']['delete'])

    @responses.activate
    def test_returns_node_files_list(self):
        self._prepare_mock_wb_response(
            provider='github', files=[{'name': 'NewFile'}])
        self.add_github()
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)

        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')

    @responses.activate
    def test_returns_folder_metadata_not_children(self):
        folder = GithubFolder(
            name='Folder',
            node=self.project,
            path='/Folder/'
        )
        folder.save()
        self._prepare_mock_wb_response(provider='github', files=[{'name': 'Folder'}], path='/Folder/')
        self.add_github()
        url = '/{}nodes/{}/files/github/Folder/'.format(API_BASE, self.project._id)
        res = self.app.get(url, params={'info': ''}, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['kind'], 'folder')
        assert_equal(res.json['data'][0]['attributes']['name'], 'Folder')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')

    @responses.activate
    def test_returns_node_file(self):
        self._prepare_mock_wb_response(
            provider='github', files=[{'name': 'NewFile'}],
            folder=False, path='/file')
        self.add_github()
        url = '/{}nodes/{}/files/github/file'.format(
            API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        # test create
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')
        assert_equal(res.json['data']['attributes']['provider'], 'github')

        # test get
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')
        assert_equal(res.json['data']['attributes']['provider'], 'github')

    @responses.activate
    def test_notfound_node_file_returns_folder(self):
        self._prepare_mock_wb_response(
            provider='github', files=[{'name': 'NewFile'}],
            path='/file')
        url = '/{}nodes/{}/files/github/file'.format(
            API_BASE, self.project._id)
        res = self.app.get(
            url, auth=self.user.auth,
            expect_errors=True,
            headers={'COOKIE': 'foo=bar;'}  # Webtests doesnt support cookies?
        )
        assert_equal(res.status_code, 404)

    @responses.activate
    def test_notfound_node_folder_returns_file(self):
        self._prepare_mock_wb_response(
            provider='github', files=[{'name': 'NewFile'}],
            folder=False, path='/')

        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(
            url, auth=self.user.auth,
            expect_errors=True,
            headers={'COOKIE': 'foo=bar;'}  # Webtests doesnt support cookies?
        )
        assert_equal(res.status_code, 404)

    @responses.activate
    def test_waterbutler_server_error_returns_503(self):
        self._prepare_mock_wb_response(status_code=500)
        self.add_github()
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(
            url, auth=self.user.auth,
            expect_errors=True,
            headers={'COOKIE': 'foo=bar;'}  # Webtests doesnt support cookies?
        )
        assert_equal(res.status_code, 503)

    @responses.activate
    def test_waterbutler_invalid_data_returns_503(self):
        wb_url = waterbutler_api_url_for(self.project._id, _internal=True, provider='github', path='/', meta=True)
        self.add_github()
        responses.add(
            responses.Response(
                responses.GET,
                wb_url,
                body=json.dumps({}),
                status=400
            )
        )
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 503)

    @responses.activate
    def test_handles_unauthenticated_waterbutler_request(self):
        self._prepare_mock_wb_response(status_code=401)
        self.add_github()
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @responses.activate
    def test_handles_notfound_waterbutler_request(self):
        invalid_provider = 'gilkjadsflhub'
        self._prepare_mock_wb_response(
            status_code=404, provider=invalid_provider)
        url = '/{}nodes/{}/files/{}/'.format(API_BASE,
                                             self.project._id, invalid_provider)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_handles_request_to_provider_not_configured_on_project(self):
        provider = 'box'
        url = '/{}nodes/{}/files/{}/'.format(
            API_BASE, self.project._id, provider)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_false(self.project.get_addon(provider))
        assert_equal(res.status_code, 404)
        assert_equal(
            res.json['errors'][0]['detail'],
            'The {} provider is not configured for this project.'.format(provider))

    @responses.activate
    def test_handles_bad_waterbutler_request(self):
        wb_url = waterbutler_api_url_for(self.project._id, _internal=True, provider='github', path='/', meta=True)
        responses.add(
            responses.Response(
                responses.GET,
                wb_url,
                json={'bad' : 'json'},
                status=418
            )
        )
        self.add_github()
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 503)
        assert_in('detail', res.json['errors'][0])

    def test_files_list_contains_relationships_object(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert 'relationships' in res.json['data'][0]


class TestNodeFilesListFiltering(ApiTestCase):

    def setUp(self):
        super(TestNodeFilesListFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        # Prep HTTP mocks
        prepare_mock_wb_response(
            node=self.project, provider='github',
            files=[
                {'name': 'abc', 'path': '/abc/', 'materialized': '/abc/', 'kind': 'folder'},
                {'name': 'xyz', 'path': '/xyz', 'materialized': '/xyz', 'kind': 'file'},
            ]
        )

    def add_github(self):
        user_auth = Auth(self.user)
        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.add_addon('github')
        self.user.external_accounts.add(oauth_settings)
        self.user.save()
        addon.user_settings = self.user.get_addon('github')
        addon.external_account = oauth_settings
        addon.save()
        self.project.save()
        addon.user_settings.oauth_grants[self.project._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()

    @responses.activate
    def test_node_files_are_filterable_by_name(self):
        url = '/{}nodes/{}/files/github/?filter[name]=xyz'.format(
            API_BASE, self.project._id)
        self.add_github()

        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'abc'
        assert_equal(res.json['data'][0]['attributes']['name'], 'xyz')

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'abc'
        assert_equal(res.json['data'][0]['attributes']['name'], 'xyz')

    @responses.activate
    def test_node_files_filter_by_name_case_insensitive(self):
        url = '/{}nodes/{}/files/github/?filter[name]=XYZ'.format(
            API_BASE, self.project._id)
        self.add_github()

        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # filters out 'abc', but finds 'xyz'
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['name'], 'xyz')

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # filters out 'abc', but finds 'xyz'
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['name'], 'xyz')

    @responses.activate
    def test_node_files_are_filterable_by_path(self):
        url = '/{}nodes/{}/files/github/?filter[path]=abc'.format(
            API_BASE, self.project._id)
        self.add_github()

        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')

    @responses.activate
    def test_node_files_are_filterable_by_kind(self):
        url = '/{}nodes/{}/files/github/?filter[kind]=folder'.format(
            API_BASE, self.project._id)
        self.add_github()

        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')

    @responses.activate
    def test_node_files_external_provider_can_filter_by_last_touched(self):
        yesterday_stamp = timezone.now() - datetime.timedelta(days=1)
        self.add_github()
        url = '/{}nodes/{}/files/github/?filter[last_touched][gt]={}'.format(
            API_BASE, self.project._id, yesterday_stamp.isoformat())
        # test create
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

        # test get
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

    def test_node_files_osfstorage_cannot_filter_by_last_touched(self):
        yesterday_stamp = timezone.now() - datetime.timedelta(days=1)
        self.file = api_utils.create_test_file(self.project, self.user)

        url = '/{}nodes/{}/files/osfstorage/?filter[last_touched][gt]={}'.format(
            API_BASE, self.project._id, yesterday_stamp.isoformat())

        # test create
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)

        # test get
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)


class TestNodeFilesListPagination(ApiTestCase):
    def setUp(self):
        super(TestNodeFilesListPagination, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def add_github(self):
        user_auth = Auth(self.user)
        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.add_addon('github')
        self.user.external_accounts.add(oauth_settings)
        self.user.save()
        addon.user_settings = self.user.get_addon('github')
        addon.external_account = oauth_settings
        addon.save()
        self.project.save()
        addon.user_settings.oauth_grants[self.project._id] = {
            oauth_settings._id: []}
        addon.user_settings.save()

    def check_file_order(self, resp):
        previous_file_name = 0
        for file in resp.json['data']:
            int_file_name = int(file['attributes']['name'])
            assert int_file_name > previous_file_name, 'Files were not in order'
            previous_file_name = int_file_name

    @responses.activate
    def test_node_files_are_sorted_correctly(self):
        prepare_mock_wb_response(
            node=self.project, provider='github',
            files=[
                {'name': '01', 'path': '/01/', 'materialized': '/01/', 'kind': 'folder'},
                {'name': '02', 'path': '/02', 'materialized': '/02', 'kind': 'file'},
                {'name': '03', 'path': '/03/', 'materialized': '/03/', 'kind': 'folder'},
                {'name': '04', 'path': '/04', 'materialized': '/04', 'kind': 'file'},
                {'name': '05', 'path': '/05/', 'materialized': '/05/', 'kind': 'folder'},
                {'name': '06', 'path': '/06', 'materialized': '/06', 'kind': 'file'},
                {'name': '07', 'path': '/07/', 'materialized': '/07/', 'kind': 'folder'},
                {'name': '08', 'path': '/08', 'materialized': '/08', 'kind': 'file'},
                {'name': '09', 'path': '/09/', 'materialized': '/09/', 'kind': 'folder'},
                {'name': '10', 'path': '/10', 'materialized': '/10', 'kind': 'file'},
                {'name': '11', 'path': '/11/', 'materialized': '/11/', 'kind': 'folder'},
                {'name': '12', 'path': '/12', 'materialized': '/12', 'kind': 'file'},
                {'name': '13', 'path': '/13/', 'materialized': '/13/', 'kind': 'folder'},
                {'name': '14', 'path': '/14', 'materialized': '/14', 'kind': 'file'},
                {'name': '15', 'path': '/15/', 'materialized': '/15/', 'kind': 'folder'},
                {'name': '16', 'path': '/16', 'materialized': '/16', 'kind': 'file'},
                {'name': '17', 'path': '/17/', 'materialized': '/17/', 'kind': 'folder'},
                {'name': '18', 'path': '/18', 'materialized': '/18', 'kind': 'file'},
                {'name': '19', 'path': '/19/', 'materialized': '/19/', 'kind': 'folder'},
                {'name': '20', 'path': '/20', 'materialized': '/20', 'kind': 'file'},
                {'name': '21', 'path': '/21/', 'materialized': '/21/', 'kind': 'folder'},
                {'name': '22', 'path': '/22', 'materialized': '/22', 'kind': 'file'},
                {'name': '23', 'path': '/23/', 'materialized': '/23/', 'kind': 'folder'},
                {'name': '24', 'path': '/24', 'materialized': '/24', 'kind': 'file'},
            ]
        )
        self.add_github()
        url = '/{}nodes/{}/files/github/?page[size]=100'.format(
            API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        self.check_file_order(res)


class TestNodeProviderDetail(ApiTestCase):

    def setUp(self):
        super(TestNodeProviderDetail, self).setUp()
        self.user = AuthUserFactory()
        self.public_project = ProjectFactory(is_public=True)
        self.private_project = ProjectFactory(creator=self.user)
        self.public_url = '/{}nodes/{}/files/providers/osfstorage/'.format(
            API_BASE, self.public_project._id)
        self.private_url = '/{}nodes/{}/files/providers/osfstorage/'.format(
            API_BASE, self.private_project._id)

    def test_can_view_if_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['id'],
            '{}:osfstorage'.format(self.private_project._id)
        )

    def test_can_view_if_public(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['id'],
            '{}:osfstorage'.format(self.public_project._id)
        )

    def test_cannot_view_if_private(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
