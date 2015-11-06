import json

from nose.tools import *  # flake8: noqa
import httpretty

from framework.auth.core import Auth

from website.addons.github import model
from website.models import Node
from website.util import waterbutler_api_url_for
from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

def prepare_mock_wb_response(
        node=None,
        provider='github',
        files=None,
        folder=True,
        path='/',
        method=httpretty.GET,
        status_code=200
    ):
    """Prepare a mock Waterbutler response with httpretty.

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
    wb_url = waterbutler_api_url_for(node._id, provider=provider, path=path, meta=True)

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

    body = json.dumps({
        u'data': jsonapi_data
    })
    httpretty.register_uri(
        method,
        wb_url,
        body=body,
        status=status_code,
        content_type='application/json'
    )

class TestNodeFilesList(ApiTestCase):

    def setUp(self):
        super(TestNodeFilesList, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.private_url = '/{}nodes/{}/files/'.format(API_BASE, self.project._id)

        self.user_two = AuthUserFactory()

        self.public_project = ProjectFactory(creator=self.user, is_public=True)
        self.public_url = '/{}nodes/{}/files/'.format(API_BASE, self.public_project._id)
        httpretty.enable()

    def tearDown(self):
        super(TestNodeFilesList, self).tearDown()
        httpretty.disable()
        httpretty.reset()

    def _prepare_mock_wb_response(self, node=None, **kwargs):
        prepare_mock_wb_response(node=node or self.project, **kwargs)

    def test_returns_public_files_logged_out(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_returns_public_files_logged_in(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_file_data(self):
        fobj = self.project.get_addon('osfstorage').get_root().append_file('NewFile')
        fobj.save()
        res = self.app.get('{}osfstorage/{}'.format(self.private_url, fobj._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_true(isinstance(res.json['data'], dict))
        assert_equal(res.content_type, 'application/vnd.api+json')
        assert_equal(res.json['data']['attributes']['kind'], 'file')
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')

    def test_returns_folder_data(self):
        fobj = self.project.get_addon('osfstorage').get_root().append_folder('NewFolder')
        fobj.save()
        res = self.app.get('{}osfstorage/{}/'.format(self.private_url, fobj._id), auth=self.user.auth)
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
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

    def test_returns_private_files_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_returns_addon_folders(self):
        user_auth = Auth(self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.json['data'][0]['attributes']['provider'], 'osfstorage')

        self.project.add_addon('github', auth=user_auth)
        addon = self.project.get_addon('github')
        addon.repo = 'something'
        addon.user = 'someone'
        oauth_settings = model.AddonGitHubOauthSettings(github_user_id='plstowork', oauth_access_token='foo')
        oauth_settings.save()
        user_settings = model.AddonGitHubUserSettings(oauth_settings=oauth_settings)
        user_settings.save()
        addon.user_settings = user_settings
        addon.save()
        self.project.save()
        res = self.app.get(self.private_url, auth=self.user.auth)
        data = res.json['data']
        providers = [item['attributes']['provider'] for item in data]
        assert_equal(len(data), 2)
        assert_in('github', providers)
        assert_in('osfstorage', providers)

    def test_returns_node_files_list(self):
        self._prepare_mock_wb_response(provider='github', files=[{'name': 'NewFile'}])
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')

    def test_returns_node_file(self):
        self._prepare_mock_wb_response(provider='github', files=[{'name': 'NewFile'}], folder=False, path='/file')
        url = '/{}nodes/{}/files/github/file'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')
        assert_equal(res.json['data']['attributes']['provider'], 'github')

    def test_notfound_node_file_returns_folder(self):
        self._prepare_mock_wb_response(provider='github', files=[{'name': 'NewFile'}], path='/file')
        url = '/{}nodes/{}/files/github/file'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 404)

    def test_notfound_node_folder_returns_file(self):
        self._prepare_mock_wb_response(provider='github', files=[{'name': 'NewFile'}], folder=False, path='/')

        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 404)

    def test_waterbutler_server_error_returns_503(self):
        self._prepare_mock_wb_response(status_code=500)
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 503)

    def test_waterbutler_invalid_data_returns_503(self):
        wb_url = waterbutler_api_url_for(self.project._id, provider='github', path='/', meta=True)
        httpretty.register_uri(
            httpretty.GET,
            wb_url,
            body=json.dumps({}),
            status=400
        )
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 503)

    def test_handles_unauthenticated_waterbutler_request(self):
        self._prepare_mock_wb_response(status_code=401)
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    def test_handles_notfound_waterbutler_request(self):
        invalid_provider = 'gilkjadsflhub'
        self._prepare_mock_wb_response(status_code=404, provider=invalid_provider)
        url = '/{}nodes/{}/files/{}/'.format(API_BASE, self.project._id, invalid_provider)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])

    def test_handles_bad_waterbutler_request(self):
        wb_url = waterbutler_api_url_for(self.project._id, provider='github', path='/', meta=True)
        httpretty.register_uri(
            httpretty.GET,
            wb_url,
            body=json.dumps({}),
            status=418
        )
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
        httpretty.enable()
        # Prep HTTP mocks
        prepare_mock_wb_response(
            node=self.project,
            provider='github',
            files=[
                {'name': 'abc', 'path': '/abc/', 'materialized': '/abc/', 'kind': 'folder'},
                {'name': 'xyz', 'path': '/xyz', 'materialized': '/xyz', 'kind': 'file'},
            ]
        )

    def tearDown(self):
        super(TestNodeFilesListFiltering, self).tearDown()
        httpretty.disable()
        httpretty.reset()

    def test_node_files_are_filterable_by_name(self):
        url = '/{}nodes/{}/files/github/?filter[name]=xyz'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)  # filters out 'abc'
        assert_equal(res.json['data'][0]['attributes']['name'], 'xyz')

    def test_node_files_are_filterable_by_path(self):
        url = '/{}nodes/{}/files/github/?filter[path]=abc'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')

    def test_node_files_are_filterable_by_kind(self):
        url = '/{}nodes/{}/files/github/?filter[kind]=folder'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)  # filters out 'xyz'
        assert_equal(res.json['data'][0]['attributes']['name'], 'abc')



