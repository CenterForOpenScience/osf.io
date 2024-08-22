import pytest
from urllib.parse import urlparse, parse_qs
from unittest import mock
import responses
from rest_framework import status as http_status
from waffle.testutils import override_flag
from urllib.parse import (
    urlencode,
    parse_qsl,
    urlunparse,
)

from addons.base.tests.base import OAuthAddonTestCaseMixin
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf_tests.factories import AuthUserFactory, ProjectFactory
from osf.utils import permissions
from osf.features import ENABLE_GV
from website.util import api_url_for, web_url_for
from website.settings import GRAVYVALET_URL


class OAuthAddonAuthViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    @property
    def ADDON_SHORT_NAME(self):
        raise NotImplementedError()

    @property
    def ExternalAccountFactory(self):
        raise NotImplementedError()

    @property
    def Provider(self):
        raise NotImplementedError()

    def test_oauth_start(self):
        url = api_url_for(
            'oauth_connect',
            service_name=self.ADDON_SHORT_NAME
        )
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_302_FOUND
        redirect_url = urlparse(res.location)
        redirect_params = parse_qs(redirect_url.query)
        provider_url = urlparse(self.Provider().auth_url)
        provider_params = parse_qs(provider_url.query)
        for param, value in redirect_params.items():
            if param == 'state':  # state may change between calls
                continue
            assert value == provider_params[param]

    def test_oauth_finish(self):
        url = web_url_for(
            'oauth_callback',
            service_name=self.ADDON_SHORT_NAME
        )
        with mock.patch.object(self.Provider, 'auth_callback') as mock_callback:
            mock_callback.return_value = True
            res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        name, args, kwargs = mock_callback.mock_calls[0]
        assert kwargs['user']._id == self.user._id

    @mock.patch('website.oauth.views.requests.get')
    def test_oauth_finish_enable_gv(self, mock_requests_get):
        url = web_url_for(
            'oauth_callback',
            service_name=self.ADDON_SHORT_NAME
        )
        query_params = {
            'code': 'somecode',
            'state': 'somestatetoken',
        }
        with override_flag(ENABLE_GV, active=True):
            request_url = urlunparse(urlparse(url)._replace(query=urlencode(query_params)))
            res = self.app.get(request_url, auth=self.user.auth)
        gv_callback_url = mock_requests_get.call_args[0][0]
        parsed_callback_url = urlparse(gv_callback_url)
        assert parsed_callback_url.netloc == urlparse(GRAVYVALET_URL).netloc
        assert parsed_callback_url.path == '/v1/oauth/callback'
        assert dict(parse_qsl(parsed_callback_url.query)) == query_params

    def test_delete_external_account(self):
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.user.reload()
        for account in self.user.external_accounts.all():
            assert account._id != self.external_account._id
        assert not self.user.external_accounts.exists()

    def test_delete_external_account_not_owner(self):
        other_user = AuthUserFactory()
        url = api_url_for(
            'oauth_disconnect',
            external_account_id=self.external_account._id
        )
        res = self.app.delete(url, auth=other_user.auth)
        assert res.status_code == http_status.HTTP_403_FORBIDDEN


class OAuthAddonConfigViewsTestCaseMixin(OAuthAddonTestCaseMixin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.node_settings = None

    @property
    def ADDON_SHORT_NAME(self):
        raise NotImplementedError()

    @property
    def ExternalAccountFactory(self):
        raise NotImplementedError()

    @property
    def folder(self):
        raise NotImplementedError("This test suite must expose a 'folder' property.")

    @property
    def Serializer(self):
        raise NotImplementedError()

    @property
    def client(self):
        raise NotImplementedError()

    def test_import_auth(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.add(ea)
        self.user.save()

        node = ProjectFactory(creator=self.user)
        node_settings = node.get_or_add_addon(self.ADDON_SHORT_NAME, auth=Auth(self.user))
        node.save()
        url = node.api_url_for(f'{self.ADDON_SHORT_NAME}_import_auth')
        res = self.app.put(url, json={
            'external_account_id': ea._id
        }, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        node_settings.reload()
        assert node_settings.external_account._id == ea._id

        node.reload()
        last_log = node.logs.latest()
        assert last_log.action == f'{self.ADDON_SHORT_NAME}_node_authorized'

    def test_import_auth_invalid_account(self):
        ea = self.ExternalAccountFactory()

        node = ProjectFactory(creator=self.user)
        node.add_addon(self.ADDON_SHORT_NAME, auth=self.auth)
        node.save()
        url = node.api_url_for(f'{self.ADDON_SHORT_NAME}_import_auth')
        res = self.app.put(url, json={
            'external_account_id': ea._id
        }, auth=self.user.auth, )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_import_auth_cant_write_node(self):
        ea = self.ExternalAccountFactory()
        user = AuthUserFactory()
        user.add_addon(self.ADDON_SHORT_NAME, auth=Auth(user))
        user.external_accounts.add(ea)
        user.save()

        node = ProjectFactory(creator=self.user)
        node.add_contributor(user, permissions=permissions.READ, auth=self.auth, save=True)
        node.add_addon(self.ADDON_SHORT_NAME, auth=self.auth)
        node.save()
        url = node.api_url_for(f'{self.ADDON_SHORT_NAME}_import_auth')
        res = self.app.put(url, json={
            'external_account_id': ea._id
        }, auth=user.auth, )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_set_config(self):
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_set_config')
        res = self.app.put(url, json={
            'selected': self.folder
        }, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.project.reload()
        assert self.project.logs.latest().action == f'{self.ADDON_SHORT_NAME}_folder_selected'
        assert res.json['result']['folder']['path'] == self.folder['path']

    def test_get_config(self):
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        with mock.patch.object(type(self.Serializer()), 'credentials_are_valid', return_value=True):
            res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'result' in res.json
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
            self.client
        )
        assert serialized == res.json['result']

    def test_get_config_unauthorized(self):
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        user = AuthUserFactory()
        self.project.add_contributor(user, permissions=permissions.READ, auth=self.auth, save=True)
        res = self.app.get(url, auth=user.auth, )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_get_config_not_logged_in(self):
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
        res = self.app.get(url, auth=None)
        assert res.status_code == http_status.HTTP_302_FOUND

    def test_account_list_single(self):
        url = api_url_for(f'{self.ADDON_SHORT_NAME}_account_list')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'accounts' in res.json
        assert len(res.json['accounts']) == 1

    def test_account_list_multiple(self):
        ea = self.ExternalAccountFactory()
        self.user.external_accounts.add(ea)
        self.user.save()

        url = api_url_for(f'{self.ADDON_SHORT_NAME}_account_list')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'accounts' in res.json
        assert len(res.json['accounts']) == 2

    def test_account_list_not_authorized(self):
        url = api_url_for(f'{self.ADDON_SHORT_NAME}_account_list')
        res = self.app.get(url, auth=None)
        assert res.status_code == http_status.HTTP_302_FOUND

    def test_folder_list(self):
        # Note: if your addon's folder_list view makes API calls
        # then you will need to implement test_folder_list in your
        # subclass, mock any API calls, and call super.
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.save()
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_folder_list')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        # TODO test result serialization?

    def test_deauthorize_node(self):
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_deauthorize_node')
        res = self.app.delete(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.node_settings.reload()
        assert self.node_settings.external_account is None
        assert not self.node_settings.has_auth

        # A log event was saved
        self.project.reload()
        last_log = self.project.logs.latest()
        assert last_log.action == f'{self.ADDON_SHORT_NAME}_node_deauthorized'


class OAuthCitationAddonConfigViewsTestCaseMixin(OAuthAddonConfigViewsTestCaseMixin):

    def __init__(self, *args, **kwargs):
        super(OAuthAddonConfigViewsTestCaseMixin,self).__init__(*args, **kwargs)
        self.mock_verify = None
        self.node_settings = None
        self.provider = None

    @property
    def ADDON_SHORT_NAME(self):
        raise NotImplementedError()

    @property
    def ExternalAccountFactory(self):
        raise NotImplementedError()

    @property
    def folder(self):
        raise NotImplementedError()

    @property
    def Serializer(self):
        raise NotImplementedError()

    @property
    def client(self):
        raise NotImplementedError()

    @property
    def citationsProvider(self):
        raise NotImplementedError()

    @property
    def foldersApiUrl(self):
        raise NotImplementedError()

    @property
    def documentsApiUrl(self):
        raise NotImplementedError()

    @property
    def mockResponses(self):
        raise NotImplementedError()

    def setUp(self):
        super().setUp()
        self.mock_verify = mock.patch.object(
            self.client,
            '_verify_client_validity'
        )
        self.mock_verify.start()

    def tearDown(self):
        self.mock_verify.stop()
        super().tearDown()

    def test_set_config(self):
        with mock.patch.object(self.client, '_folder_metadata') as mock_metadata:
            mock_metadata.return_value = self.folder
            url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_set_config')
            res = self.app.put(url, json={
                'external_list_id': self.folder.json['id'],
                'external_list_name': self.folder.name,
            }, auth=self.user.auth)
            assert res.status_code == http_status.HTTP_200_OK
            self.project.reload()
            assert self.project.logs.latest().action == f'{self.ADDON_SHORT_NAME}_folder_selected'
            assert res.json['result']['folder']['name'] == self.folder.name

    def test_get_config(self):
        with mock.patch.object(self.client, '_folder_metadata') as mock_metadata:
            mock_metadata.return_value = self.folder
            self.node_settings.api._client = 'client'
            self.node_settings.save()
            url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_get_config')
            res = self.app.get(url, auth=self.user.auth)
            assert res.status_code == http_status.HTTP_200_OK
            assert 'result' in res.json
            result = res.json['result']
            serialized = self.Serializer(
                node_settings=self.node_settings,
                user_settings=self.node_settings.user_settings
            ).serialized_node_settings
            serialized['validCredentials'] = self.citationsProvider().check_credentials(self.node_settings)
            assert serialized == result

    def test_folder_list(self):
        with mock.patch.object(self.client, '_get_folders'):
            self.node_settings.set_auth(self.external_account, self.user)
            self.node_settings.save()
            url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_citation_list')
            res = self.app.get(url, auth=self.user.auth)
            assert res.status_code == http_status.HTTP_200_OK

    def test_check_credentials(self):
        with mock.patch.object(self.client, 'client', new_callable=mock.PropertyMock) as mock_client:
            self.provider = self.citationsProvider()
            mock_client.side_effect = HTTPError(403)
            assert not self.provider.check_credentials(self.node_settings)

            mock_client.side_effect = HTTPError(402)
            with pytest.raises(HTTPError):
                self.provider.check_credentials(self.node_settings)

    def test_widget_view_complete(self):
        # JSON: everything a widget needs
        self.citationsProvider().set_config(
            self.node_settings,
            self.user,
            self.folder.json['id'],
            self.folder.name,
            Auth(self.user)
        )
        assert self.node_settings.complete
        assert self.node_settings.list_id == 'Fake Key'

        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))

        assert res['complete']
        assert res['list_id'] == 'Fake Key'

    def test_widget_view_incomplete(self):
        # JSON: tell the widget when it hasn't been configured
        self.node_settings.clear_settings()
        self.node_settings.save()
        assert not self.node_settings.complete
        assert self.node_settings.list_id is None

        res = self.citationsProvider().widget(self.project.get_addon(self.ADDON_SHORT_NAME))

        assert not res['complete']
        assert res['list_id'] is None

    @responses.activate
    def test_citation_list_root(self):

        responses.add(
            responses.Response(
                responses.GET,
                self.foldersApiUrl,
                body=self.mockResponses['folders'],
                content_type='application/json'
            )
        )

        res = self.app.get(
            self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_citation_list'),
            auth=self.user.auth
        )
        root = res.json['contents'][0]
        assert root['kind'] == 'folder'
        assert root['id'] == 'ROOT'
        assert root['parent_list_id'] == '__'

    @responses.activate
    def test_citation_list_non_root(self):

        responses.add(
            responses.Response(
                responses.GET,
                self.foldersApiUrl,
                body=self.mockResponses['folders'],
                content_type='application/json'
            )
        )

        responses.add(
            responses.Response(
                responses.GET,
                self.documentsApiUrl,
                body=self.mockResponses['documents'],
                content_type='application/json'
            )
        )

        res = self.app.get(
            self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_citation_list', list_id='ROOT'),
            auth=self.user.auth
        )

        children = res.json['contents']
        assert len(children) == 7
        assert children[0]['kind'] == 'folder'
        assert children[1]['kind'] == 'file'
        assert children[1].get('csl') is not None

    @responses.activate
    def test_citation_list_non_linked_or_child_non_authorizer(self):
        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)

        self.node_settings.list_id = 'e843da05-8818-47c2-8c37-41eebfc4fe3f'
        self.node_settings.save()

        responses.add(
            responses.Response(
                responses.GET,
                self.foldersApiUrl,
                body=self.mockResponses['folders'],
                content_type='application/json'
            )
        )

        responses.add(
            responses.Response(
                responses.GET,
                self.documentsApiUrl,
                body=self.mockResponses['documents'],
                content_type='application/json'
            )
        )

        res = self.app.get(
            self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_citation_list', list_id='ROOT'),
            auth=non_authorizing_user.auth,
        )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN
