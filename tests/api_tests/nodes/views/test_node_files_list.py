# -*- coding: utf-8 -*-
import mock
import base64
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth

from website.addons.github import model
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
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

    @mock.patch('api.nodes.views.requests.get')
    def test_returns_node_files_list(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': [{
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/',
                u'provider': u'github',
                u'size': None,
                u'materialized': '/',
            }]
        }
        auth_header = 'Basic {}'.format(base64.b64encode(':'.join(self.user.auth)))
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.json['data'][0]['attributes']['name'], 'NewFile')
        assert_equal(res.json['data'][0]['attributes']['provider'], 'github')
        mock_waterbutler_request.assert_called_once_with(
            'http://localhost:7777/v1/resources/{}/providers/github/?meta=True'.format(self.project._id),
            cookies={'foo':'bar'},
            headers={'Authorization': auth_header}
        )

    @mock.patch('api.nodes.views.requests.get')
    def test_returns_node_file(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': {
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/NewFile',
                u'provider': u'github',
                u'size': None,
                u'materialized': '/',
            }
        }
        auth_header = 'Basic {}'.format(base64.b64encode(':'.join(self.user.auth)))
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/github/file'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.json['data']['attributes']['name'], 'NewFile')
        assert_equal(res.json['data']['attributes']['provider'], 'github')
        mock_waterbutler_request.assert_called_once_with(
            'http://localhost:7777/v1/resources/{}/providers/github/file?meta=True'.format(self.project._id),
            cookies={'foo':'bar'},
            headers={'Authorization': auth_header}
        )

    @mock.patch('api.nodes.views.requests.get')
    def test_notfound_node_file_returns_folder(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': [{
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/NewFile',
                u'provider': u'github',
                u'size': None,
                u'materialized': '/',
            }]
        }
        auth_header = 'Basic {}'.format(base64.b64encode(':'.join(self.user.auth)))
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/github/file'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 404)

    @mock.patch('api.nodes.views.requests.get')
    def test_notfound_node_folder_returns_file(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            u'data': {
                u'contentType': None,
                u'extra': {u'downloads': 0, u'version': 1},
                u'kind': u'file',
                u'modified': None,
                u'name': u'NewFile',
                u'path': u'/NewFile',
                u'provider': u'github',
                u'size': None,
                u'materialized': '/',
            }
        }
        auth_header = 'Basic {}'.format(base64.b64encode(':'.join(self.user.auth)))
        mock_waterbutler_request.return_value = mock_res

        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 404)

    @mock.patch('api.nodes.views.requests.get')
    def test_waterbutler_server_error_returns_503(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 500
        mock_waterbutler_request.return_value = mock_res
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 503)

    @mock.patch('api.nodes.views.requests.get')
    def test_waterbutler_invalid_data_returns_503(self, mock_waterbutler_request):
        mock_res = mock.MagicMock()
        mock_res.status_code = 400
        mock_res.json.return_value = {}  # no data
        mock_waterbutler_request.return_value = mock_res
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True, headers={
            'COOKIE': 'foo=bar;'  # Webtests doesnt support cookies?
        })
        assert_equal(res.status_code, 503)

    @mock.patch('api.nodes.views.requests.get')
    def test_handles_unauthenticated_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 401
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_in('detail', res.json['errors'][0])

    @mock.patch('api.nodes.views.requests.get')
    def test_handles_notfound_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/gilkjadsflhub/'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 404
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_in('detail', res.json['errors'][0])


    @mock.patch('api.nodes.views.requests.get')
    def test_handles_bad_waterbutler_request(self, mock_waterbutler_request):
        url = '/{}nodes/{}/files/github/'.format(API_BASE, self.project._id)
        mock_res = mock.MagicMock()
        mock_res.status_code = 418
        mock_res.json.return_value = {}
        mock_waterbutler_request.return_value = mock_res
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 503)
        assert_in('detail', res.json['errors'][0])

    def test_files_list_contains_relationships_object(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert 'relationships' in res.json['data'][0]
